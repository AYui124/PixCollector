"""API路由模块."""
import logging
from contextlib import suppress
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import and_, func, or_, select

from auth import pixiv_auth
from collector import PixivCollector
from database import db
from models import (
    Artwork,
    CollectionLog,
    Follow,
    SchedulerConfig,
    SystemConfig,
    User,
)
from rate_limiter import RateLimiter
from scheduler import task_scheduler
from updater import ArtworkUpdater

logger = logging.getLogger(__name__)

# 创建API蓝图
api = Blueprint('api', __name__)


@api.route('/init/check', methods=['GET'])
def check_init():
    """检查系统是否已初始化."""
    is_initialized = db.session.query(User).count() > 0
    return jsonify({'initialized': is_initialized})


@api.route('/init', methods=['POST'])
def init_system():
    """初始化系统，创建管理员账户."""
    if db.session.query(User).count() > 0:
        return jsonify({
            'success': False,
            'message': 'System already initialized'
        }), 400

    username = current_app.config.get("ADMIN_USER")
    password = current_app.config.get("ADMIN_PWD")

    if not password or len(password) < 6:
        return jsonify({
            'success': False,
            'message': 'Password must be at least 6 characters'
        }), 400

    # 创建管理员
    admin = User(username=username, is_admin=True)
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'System initialized successfully'
    })


@api.route('/config/tokens', methods=['POST'])
@login_required
def update_tokens():
    """更新Pixiv Token."""
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    access_token = data.get('access_token')

    if not refresh_token:
        return jsonify({
            'success': False,
            'message': 'refresh_token is required'
        }), 400

    # 如果没有提供access_token，使用refresh_token获取
    logger.info('r=%s,a=%s', refresh_token, access_token)
    if not access_token:
        logger.info('no access_token, refreshing...')
        pixiv_auth.refresh_token = refresh_token
        if pixiv_auth.refresh_access_token():
            access_token = pixiv_auth.access_token
            return jsonify({
                'success': True,
                'message': 'Tokens refreshed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to refresh tokens'
            }), 400

    # 保存两个token
    if pixiv_auth.save_tokens(access_token, refresh_token):
        return jsonify({
            'success': True,
            'message': 'Tokens saved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to save tokens'
        }), 500


@api.route('/config/test', methods=['POST'])
@login_required
def test_connection():
    """测试Pixiv连接."""
    success = pixiv_auth.ensure_authenticated()
    if success:
        return jsonify({'success': True, 'message': 'token检测成功'})
    else:
        return jsonify({'success': False, 'message': 'token检测失败'}), 500


@api.route('/collect/daily', methods=['POST'])
@login_required
def collect_daily():
    """手动触发每日排行采集."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_daily_rank()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual daily collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/weekly', methods=['POST'])
@login_required
def collect_weekly():
    """手动触发每周排行采集."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_weekly_rank()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual weekly collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/monthly', methods=['POST'])
@login_required
def collect_monthly():
    """手动触发每月排行采集."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_monthly_rank()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual monthly collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/sync-follows', methods=['POST'])
@login_required
def sync_follows():
    """手动触发关注列表同步."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.sync_follows()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual follow sync failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/follow-user-artworks', methods=['POST'])
@login_required
def collect_follow_user_artworks():
    """手动触发初始全量关注采集."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_follow_user_artworks()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual follow user artworks collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/user-artworks', methods=['POST'])
@login_required
def collect_single_user_artworks():
    """手动触发单个用户作品采集."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id is required'
            }), 400

        # 查找用户
        follow = db.session.query(Follow).filter_by(user_id=user_id).first()
        if not follow:
            return jsonify({
                'success': False,
                'message': 'User not found in follow list'
            }), 404

        # 获取回采年限配置
        config = db.session.query(SystemConfig).filter_by(
            config_key='new_user_backtrack_years'
        ).first()
        backtrack_years = (config.int_value() or 2) if config else 2
        # 执行采集
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_user_artworks(
            follow, backtrack_years, True
        )

        return jsonify({
            'success': True,
            'user_name': follow.user_name,
            'new_count': result['new_count']
        })
    except Exception as e:
        logger.error(f"Manual single user artworks collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/follow-new-works', methods=['POST'])
@login_required
def collect_follow_new_works():
    """手动触发关注用户新作品采集."""
    try:
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.collect_follow_works()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual follow new works collection failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/update-artworks', methods=['POST'])
@login_required
def update_artworks():
    """手动触发作品元数据更新."""
    try:
        limiter = RateLimiter()
        updater = ArtworkUpdater(limiter)
        result = updater.update_artworks()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Manual artwork update failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/cleanup-logs', methods=['POST'])
@login_required
def clean_up_logs():
    """手动触发旧日志清理."""
    try:
        # 获取保留天数配置
        # 执行清理
        limiter = RateLimiter()
        collector = PixivCollector(limiter)
        result = collector.clean_up_old_logs()
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"Manual log cleanup failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api.route('/collect/status', methods=['GET'])
@login_required
def get_collect_status():
    """获取采集状态."""
    # 获取最新日志
    recent_logs = db.session.query(CollectionLog).order_by(
        CollectionLog.created_at.desc()
    ).limit(10).all()

    # 获取统计信息
    total_artworks = db.session.query(Artwork).count()
    valid_artworks = db.session.query(Artwork).filter_by(is_valid=True).count()
    total_follows = db.session.query(Follow).count()

    return jsonify({
        'success': True,
        'stats': {
            'total_artworks': total_artworks,
            'valid_artworks': valid_artworks,
            'total_follows': total_follows
        },
        'recent_logs': [log.to_dict() for log in recent_logs]
    })


@api.route('/collect/logs', methods=['GET'])
@login_required
def get_collect_logs():
    """获取采集日志."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    log_type = request.args.get('type', None)
    status = request.args.get('status', None)

    query = select(CollectionLog)

    if log_type:
        query = query.where(CollectionLog.log_type == log_type)
    if status:
        query = query.where(CollectionLog.status == status)
    query = query.order_by(CollectionLog.created_at.desc())
    pagination: Pagination = db.paginate(
        query,
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'logs': [log.to_dict() for log in pagination.items]
    })


@api.route('/artworks', methods=['GET'])
@login_required
def get_artworks():
    """获取作品列表（支持多条件过滤）."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    tags_param = request.args.get('tags', '')
    tags_match = request.args.get('tags_match', 'or', type=str)
    is_r18_param = request.args.get('is_r18', 'all', type=str)
    type_param = request.args.get('type', 'all', type=str)
    collect_type_param = request.args.get('collect_type', 'all', type=str)
    author_name = request.args.get('author', '', type=str)
    illust_id = request.args.get('illust_id', '', type=str)
    is_valid_param = request.args.get('is_valid', 'all', type=str)
    post_date_start = request.args.get('post_date_start', '', type=str)
    post_date_end = request.args.get('post_date_end', '', type=str)

    # 参数验证
    per_page = min(max(per_page, 1), 100)
    tags_match = tags_match.lower() if tags_match in ['and', 'or'] else 'or'

    # 构建查询
    query = select(Artwork)

    # 类型过滤
    if type_param and type_param != 'all':
        valid_types = ['illust', 'manga', 'ugoira']
        if type_param in valid_types:
            query = query.where(Artwork.type == type_param)

    # 采集类型过滤
    if collect_type_param and collect_type_param != 'all':
        valid_collect_types = [
            'ranking_works',
            'follow_new_works',
            'follow_user_artworks',
            'follow_new_follow',
            'update_artworks'
        ]
        if collect_type_param in valid_collect_types:
            query = query.where(Artwork.collect_type == collect_type_param)

    # 标签过滤
    if tags_param:
        tags_list = [
            tag.strip() for tag in tags_param.split(',') if tag.strip()
        ]

        if tags_list:
            tag_conditions = []
            for tag in tags_list:
                tag_conditions.append(
                    db.text(f"JSON_CONTAINS(tags, '\"{tag}\"')")
                )

            if tags_match == 'and':
                query = query.where(and_(*tag_conditions))
            else:
                query = query.where(or_(*tag_conditions))

    # R18过滤
    if is_r18_param.lower() == 'true':
        query = query.where(Artwork.is_r18)
    elif is_r18_param.lower() == 'false':
        query = query.where(~Artwork.is_r18)

    # 作者名筛选（模糊匹配）
    if author_name:
        query = query.where(Artwork.author_name.like(f'%{author_name}%'))

    # illust_id精确匹配
    if illust_id:
        with suppress(ValueError):
            query = query.where(Artwork.illust_id == int(illust_id))

    # 失效状态筛选
    if is_valid_param.lower() == 'true':
        query = query.where(Artwork.is_valid)
    elif is_valid_param.lower() == 'false':
        query = query.where(~Artwork.is_valid)

    # 发布时间范围筛选
    if post_date_start:
        try:
            start_date = datetime.strptime(post_date_start, '%Y-%m-%d')
            query = query.where(Artwork.post_date >= start_date)
        except ValueError:
            pass

    if post_date_end:
        try:
            end_date = datetime.strptime(post_date_end, '%Y-%m-%d')
            query = query.where(Artwork.post_date <= end_date)
        except ValueError:
            pass

    # 按post_date降序排序
    pagination: Pagination = db.paginate(
        query.order_by(Artwork.post_date.desc()),
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'artworks': [artwork.to_dict() for artwork in pagination.items]
    })


@api.route('/artworks/<int:illust_id>', methods=['GET'])
@login_required
def get_artwork_detail(illust_id):
    """获取单个作品的所有页."""
    query = select(Artwork).where(Artwork.illust_id == illust_id)
    artworks = db.session.execute(query).scalars().all()
    if not artworks:
        return jsonify({
            'success': False,
            'message': '未找到该作品'
        })

    # 按page_index排序
    artworks = sorted(artworks, key=lambda x: x.page_index)
    return jsonify({
        'success': True,
        'artworks': [artwork.to_dict() for artwork in artworks]
    })


@api.route('/artworks/<int:artwork_id>/invalidate', methods=['PATCH'])
@login_required
def invalidate_artwork(artwork_id):
    """手动标记作品为废弃."""
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()

        # 如果没有提供原因，使用默认值
        if not reason:
            reason = 'Not like'

        # 查找并更新作品
        artwork = db.session.query(Artwork).filter_by(
            id=artwork_id
        ).first()

        if not artwork:
            return jsonify({
                'success': False,
                'message': '作品不存在'
            }), 404

        artwork.is_valid = False
        artwork.error_message = reason
        db.session.commit()

        logger.info(
            f"Artwork {artwork_id} marked as invalid by user: {reason}"
        )

        return jsonify({
            'success': True,
            'message': '已标记为废弃'
        })
    except Exception as e:
        logger.error(f"Failed to invalidate artwork {artwork_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@api.route('/artworks/by-illust/<int:illust_id>/invalidate', methods=['PATCH'])
@login_required
def invalidate_artwork_by_illust(illust_id):
    """按illust_id标记作品的所有页面为废弃."""
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()

        # 如果没有提供原因，使用默认值
        if not reason:
            reason = 'Not like'

        # 查询该illust_id的所有artworks
        artworks = db.session.query(Artwork).filter_by(
            illust_id=illust_id
        ).all()

        if not artworks:
            return jsonify({
                'success': False,
                'message': '未找到该作品'
            }), 404

        # 批量更新所有页面
        count = 0
        for artwork in artworks:
            artwork.is_valid = False
            artwork.error_message = reason
            count += 1

        db.session.commit()

        logger.info(
            f"Artwork {illust_id} ({count} pages) "
            f" marked as invalid by user: {reason}"
        )

        return jsonify({
            'success': True,
            'message': f'已标记{count}页为废弃',
            'count': count
        })
    except Exception as e:
        logger.error(f"Failed to invalidate artwork {illust_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@api.route('/random/artwork', methods=['GET'])
def get_random_artwork():
    """
    获取随机图片（支持标签过滤）.

    Query Parameters:
        limit: 返回数量（1-10，默认1）
        tags: 标签过滤，多个标签用逗号分隔（可选）
        tags_match: 标签匹配方式，'and'=所有标签，'or'=任一标签（默认'or'）
        is_r18: R18过滤，'true'=只R18，'false'=只非R18，'all'=全部（默认'all'）
    """
    limit = request.args.get('limit', 1, type=int)
    tags_param = request.args.get('tags', '')
    tags_match = request.args.get('tags_match', 'or', type=str)
    is_r18_param = request.args.get('is_r18', 'false', type=str)

    # 参数验证
    limit = min(max(limit, 1), 10)
    tags_match = tags_match.lower() if tags_match in ['and', 'or'] else 'or'

    # 构建查询
    query = select(Artwork).where(Artwork.is_valid)

    # 类型过滤（只返回illust类型）
    query = query.where(Artwork.type == 'illust')

    # 标签过滤
    if tags_param:
        tags_list = [
            tag.strip() for tag in tags_param.split(',') if tag.strip()
        ]

        if tags_list:
            tag_conditions = []
            for tag in tags_list:
                tag_conditions.append(
                    db.text(f"JSON_CONTAINS(tags, '\"{tag}\"')")
                )

            if tags_match == 'and':
                query = query.where(and_(*tag_conditions))
            else:
                query = query.where(or_(*tag_conditions))

    # R18过滤
    if is_r18_param.lower() == 'true':
        query = query.where(Artwork.is_r18)
    elif is_r18_param.lower() == 'false':
        query = query.where(~Artwork.is_r18)

    # 随机选择
    query = query.order_by(func.random()).limit(limit)
    artworks = db.session.execute(query).scalars().all()
    if not artworks:
        return jsonify({
            'success': False,
            'message': '未找到符合条件的作品'
        })

    # 获取代理URL配置
    proxy_url = current_app.config.get('PIXIV_PROXY_URL', 'https://i.pixiv.re')

    result = []
    for artwork in artworks:
        result.append({
            'illust_id': artwork.illust_id,
            'title': artwork.title,
            'author_id': artwork.author_id,
            'author_name': artwork.author_name,
            'url': artwork.url.replace('https://i.pximg.net', proxy_url),
            'share': artwork.share_url,
            'page': f'{artwork.page_index + 1} / {artwork.page_count}',
            'total_bookmarks': artwork.total_bookmarks,
            'total_view': artwork.total_view,
            'tags': artwork.tags,
            'type': artwork.type,
        })

    return jsonify({
        'success': True,
        'count': len(result),
        'artworks': result
    })


@api.route('/random/artwork/image', methods=['GET'])
def get_random_artwork_image():
    """
    获取随机图片的图片URL（直接跳转，支持标签过滤）.

    Query Parameters:
        tags: 标签过滤（可选）
        tags_match: 标签匹配方式，'and'/'or'（默认'or'）
        is_r18: R18过滤，'true'/'false'/'all'（默认'all'）
    """
    tags_param = request.args.get('tags', '')
    tags_match = request.args.get('tags_match', 'or', type=str)
    is_r18_param = request.args.get('is_r18', 'all', type=str)

    # 构建查询
    query = select(Artwork).where(Artwork.is_valid)

    # 标签过滤
    if tags_param:
        tags_list = [
            tag.strip() for tag in tags_param.split(',') if tag.strip()
        ]

        if tags_list:
            tag_conditions = []
            for tag in tags_list:
                tag_conditions.append(
                    db.text(f"JSON_CONTAINS(tags, '\"{tag}\"')")
                )

            if tags_match.lower() == 'and':
                query = query.where(and_(*tag_conditions))
            else:
                query = query.where(or_(*tag_conditions))

    # R18过滤
    if is_r18_param.lower() == 'true':
        query = query.where(Artwork.is_r18)
    elif is_r18_param.lower() == 'false':
        query = query.where(~Artwork.is_r18)

    # 获取单个随机作品
    query = query.order_by(func.random()).limit(1)
    artwork = db.session.execute(query).scalar_one_or_none()

    if not artwork:
        return jsonify({
            'success': False,
            'message': '未找到有效的作品'
        })

    # 获取代理URL配置
    proxy_url = current_app.config.get('PIXIV_PROXY_URL', 'https://i.pixiv.re')

    return jsonify({
        'success': True,
        'image_url': artwork.url.replace('https://i.pximg.net', proxy_url),
        'illust_id': artwork.illust_id,
        'title': artwork.title,
        'author_name': artwork.author_name,
        'tags': artwork.tags,
        'is_r18': artwork.is_r18
    })


@api.route('/follows', methods=['GET'])
@login_required
def get_follows():
    """获取关注用户列表."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    username = request.args.get('username', '', type=str)

    query = select(Follow)

    # 添加用户名搜索
    if username:
        query = query.where(Follow.user_name.like(f'%{username}%'))

    query = query.order_by(
        Follow.created_at.desc()
    )

    pagination: Pagination = db.paginate(
        query, page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'follows': [follow.to_dict() for follow in pagination.items]
    })


@api.route('/follows/stats', methods=['GET'])
@login_required
def get_follows_stats():
    """获取关注用户统计."""
    # 总关注用户数
    total_follows = db.session.query(Follow).count()

    # 有作品发布的用户数
    users_with_artworks = db.session.query(func.count(Follow.id)).filter(
        Follow.last_artwork_date.is_not(None)
    ).scalar()

    # 最近7天发布作品的用户数
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_users_last_7days = db.session.query(func.count(Follow.id)).filter(
        Follow.last_artwork_date >= seven_days_ago
    ).scalar()

    # 最近30天发布作品的用户数
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_users_last_30days = db.session.query(func.count(Follow.id)).filter(
        Follow.last_artwork_date >= thirty_days_ago
    ).scalar()

    # 最活跃用户
    active_users = db.session.query(Follow).filter(
        Follow.last_artwork_date.is_not(None)
    ).order_by(Follow.last_artwork_date.desc()).limit(10).all()

    return jsonify({
        'success': True,
        'stats': {
            'total_follows': total_follows,
            'users_with_artworks': users_with_artworks,
            'active_users_last_7days': active_users_last_7days,
            'active_users_last_30days': active_users_last_30days
        },
        'active_users': [user.to_dict() for user in active_users]
    })


@api.route('/config', methods=['GET'])
@login_required
def get_config():
    """获取所有配置（从SystemConfig读取）."""
    config_items = db.session.query(SystemConfig).all()

    # 将key-value转换为字典
    config_dict = {}
    for item in config_items:
        config_dict[item.config_key] = item.to_dict()['value']

    return jsonify({
        'success': True,
        'config': config_dict,
        'config_items': [item.to_dict() for item in config_items]
    })


@api.route('/config', methods=['POST'])
@login_required
def update_config():
    """更新系统配置（保存到SystemConfig）."""
    data = request.get_json()

    # 配置项的类型映射
    config_types = {
        # Pixiv认证配置
        'refresh_token': 'string',
        'access_token': 'string',
        'token_expires_at': 'datetime',

        # 采集配置
        'update_interval_days': 'integer',
        'invalid_artwork_action': 'string',
        'new_user_backtrack_years': 'integer',
        'log_retention_days': 'integer',

        # 速率限制配置
        'api_delay_min': 'float',
        'api_delay_max': 'float',
        'error_delay_429_min': 'float',
        'error_delay_429_max': 'float',
        'error_delay_403_min': 'float',
        'error_delay_403_max': 'float',
        'error_delay_other_min': 'float',
        'error_delay_other_max': 'float'
    }

    updated_count = 0
    for key, value in data.items():
        if key in config_types:
            config_item = db.session.query(SystemConfig).filter_by(
                config_key=key
            ).first()

        if not config_item:
            config_item = SystemConfig(
                config_key=key,
                value_type=config_types[key]
            )
            db.session.add(config_item)

        # 根据类型转换值
        if config_types[key] == 'datetime':
            if isinstance(value, str):
                config_value = value
            elif value:
                config_value = value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                config_value = None
        else:
            config_value = str(value) if value is not None else None

        config_item.config_value = config_value
        config_item.updated_at = datetime.now()
        updated_count += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': (
            f'Configuration updated successfully'
            f' ({updated_count} items)'
        ),
        'config': get_config_from_items()
    })


def get_config_from_items():
    """从SystemConfig获取配置字典."""
    config_items = db.session.query(SystemConfig).all()
    config_dict = {}
    for item in config_items:
        config_dict[item.config_key] = item.to_dict()['value']
    return config_dict


@api.route('/config/scheduler', methods=['GET'])
@login_required
def get_scheduler_config():
    """获取定时任务配置."""
    configs = db.session.query(SchedulerConfig).all()
    return jsonify({
        'success': True,
        'configs': [config.to_dict() for config in configs]
    })


@api.route('/config/scheduler', methods=['POST'])
@login_required
def update_scheduler_config():
    """更新定时任务配置."""
    data = request.get_json()
    jobs_config = {}

    for key, value in data.items():
        if key in [
            'ranking_works', 'follow_new_follow',
            'follow_new_works', 'update_artworks', 'cleanup_logs'
        ]:
            jobs_config[key] = value

    for job_type, job_config in jobs_config.items():
        config = db.session.query(SchedulerConfig).filter_by(
            collect_type=job_type
        ).first()

        if not config:
            config = SchedulerConfig(collect_type=job_type)
            db.session.add(config)

        if 'crontab_expression' in job_config:
            config.crontab_expression = job_config['crontab_expression']
        if 'is_active' in job_config:
            config.is_active = job_config['is_active']

        config.updated_at = datetime.now()

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Scheduler configuration updated successfully'
    })


@api.route('/scheduler/refresh', methods=['POST'])
@login_required
def refresh_scheduler():
    """刷新调度器任务（动态更新任务配置）."""
    try:
        task_scheduler.refresh_jobs()
        return jsonify({
            'success': True,
            'message': 'Scheduler jobs refreshed successfully'
        })
    except Exception as e:
        logger.error(f"Failed to refresh scheduler jobs: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to refresh scheduler: {str(e)}'
        }), 500


@api.route('/public/stats', methods=['GET'])
def get_public_stats():
    """获取公开统计信息（无需登录）."""
    # 总作品数（过滤失效）
    total_artworks = db.session.query(Artwork).filter_by(
        is_valid=True
    ).count()

    # R18作品数（过滤失效）
    r18_artworks = db.session.query(Artwork).filter_by(
        is_r18=True, is_valid=True
    ).count()

    # 非R18作品数（过滤失效）
    non_r18_artworks = db.session.query(Artwork).filter_by(
        is_r18=False, is_valid=True
    ).count()

    # 最后采集时间
    last_artwork = db.session.query(Artwork).order_by(
        Artwork.created_at.desc()
    ).first()

    last_collect_time = None
    if last_artwork and last_artwork.created_at:
        last_collect_time = last_artwork.created_at.strftime(
            '%Y-%m-%d %H:%M:%S'
        )

    # 图表数据 - R18占比
    r18_distribution = {
        'r18': r18_artworks,
        'non_r18': non_r18_artworks
    }

    # 图表数据 - 最近7天采集趋势
    daily_trend = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).date()
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())

        count = db.session.query(Artwork).filter(
            Artwork.created_at >= start_of_day,
            Artwork.created_at <= end_of_day
        ).count()

        daily_trend.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })

    return jsonify({
        'success': True,
        'stats': {
            'total_artworks': total_artworks,
            'r18_artworks': r18_artworks,
            'non_r18_artworks': non_r18_artworks,
            'last_collect_time': last_collect_time
        },
        'charts': {
            'r18_distribution': r18_distribution,
            'daily_trend': daily_trend
        }
    })


@api.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """获取统计信息."""
    # 总作品数
    total_artworks = db.session.query(Artwork).count()
    valid_artworks = db.session.query(Artwork).filter_by(is_valid=True).count()
    invalid_artworks = db.session.query(Artwork).filter_by(
        is_valid=False
    ).count()

    # 关注用户数
    total_follows = db.session.query(Follow).count()
    active_follows = db.session.query(Follow).filter(
        Follow.last_artwork_date >= datetime.now() - timedelta(days=7)
    ).count()

    # 今日采集数
    today = datetime.now().date()
    today_artworks = db.session.query(Artwork).filter(
        Artwork.created_at >= today
    ).count()

    # 今日更新数
    today_updates = db.session.query(Artwork).filter(
        Artwork.last_updated_at >= today
    ).count()

    return jsonify({
        'success': True,
        'stats': {
            'total_artworks': total_artworks,
            'valid_artworks': valid_artworks,
            'invalid_artworks': invalid_artworks,
            'total_follows': total_follows,
            'active_follows': active_follows,
            'today_artworks': today_artworks,
            'today_updates': today_updates
        }
    })
