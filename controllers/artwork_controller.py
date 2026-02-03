"""作品控制器."""
import logging
from contextlib import suppress
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required

from services import services

logger = logging.getLogger(__name__)

artwork_api = Blueprint('artwork_api', __name__)


@artwork_api.route('/artworks', methods=['GET'])
@login_required
def get_artworks():
    """获取作品列表（支持多条件过滤）."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    type_param = request.args.get('type', 'all', type=str)
    collect_type_param = request.args.get('collect_type', 'all', type=str)
    is_r18_param = request.args.get('is_r18', 'all', type=str)
    author_name = request.args.get('author', '', type=str)
    illust_id = request.args.get('illust_id', '', type=str)
    is_valid_param = request.args.get('is_valid', 'all', type=str)
    post_date_start = request.args.get('post_date_start', '', type=str)
    post_date_end = request.args.get('post_date_end', '', type=str)
    tags_param = request.args.get('tags', '', type=str)
    tags_match = request.args.get('tags_match', 'or', type=str)

    # 参数验证
    per_page = min(max(per_page, 1), 100)

    # 转换参数
    type_filter = type_param if type_param != 'all' else None
    collect_type_filter = (
        collect_type_param if collect_type_param != 'all' else None
    )
    is_r18_filter = None
    if is_r18_param.lower() == 'true':
        is_r18_filter = True
    elif is_r18_param.lower() == 'false':
        is_r18_filter = False

    is_valid_filter = None
    if is_valid_param.lower() == 'true':
        is_valid_filter = True
    elif is_valid_param.lower() == 'false':
        is_valid_filter = False

    # 日期转换
    start_date = None
    end_date = None
    if post_date_start:
        with suppress(ValueError):
            start_date = datetime.strptime(post_date_start, '%Y-%m-%d')

    if post_date_end:
        with suppress(ValueError):
            end_date = datetime.strptime(post_date_end, '%Y-%m-%d')

    # 标签过滤
    tags_filter = tags_param if tags_param else None

    # 作品ID过滤
    illust_id_filter: int | None = None
    if illust_id:
        with suppress(ValueError):
            illust_id_filter = int(illust_id)

    # 调用Service
    pagination = services.artwork.paginate_artworks(
        page=page,
        per_page=per_page,
        type_filter=type_filter,
        collect_type_filter=collect_type_filter,
        is_r18_filter=is_r18_filter,
        author_name_filter=author_name if author_name else None,
        is_valid_filter=is_valid_filter,
        post_date_start=start_date,
        post_date_end=end_date,
        tags_filter=tags_filter,
        tags_match=tags_match,
        illust_id_filter=illust_id_filter
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'artworks': [artwork.to_dict() for artwork in pagination.items]
    })


@artwork_api.route('/artworks/<int:illust_id>', methods=['GET'])
@login_required
def get_artwork_detail(illust_id):
    """获取单个作品的所有页."""
    artworks = services.artwork.get_artworks_by_illust_id(illust_id)
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


@artwork_api.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """获取统计信息."""
    stats = services.artwork.get_stats()
    return jsonify({
        'success': True,
        **stats
    })


@artwork_api.route('/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """获取dashboard统计信息."""
    # 获取artwork统计
    artwork_stats = services.artwork.get_dashboard_stats()

    # 获取follow统计
    follow_stats = services.follow.get_stats()

    # 合并统计
    combined_stats = {
        **artwork_stats,
        'total_follows': follow_stats.get('total_follows', 0),
        'active_follows': follow_stats.get('active_users_last_7days', 0)
    }

    return jsonify({
        'success': True,
        'stats': combined_stats
    })


@artwork_api.route('/artworks/<int:artwork_id>/invalidate', methods=['PATCH'])
@login_required
def invalidate_artwork(artwork_id):
    """手动标记作品为废弃."""
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()

        if not reason:
            reason = 'Not like'

        success = services.artwork.mark_page_invalid(artwork_id, reason)
        if success:
            return jsonify({
                'success': True,
                'message': '已标记为废弃'
            })
        else:
            return jsonify({
                'success': False,
                'message': '作品不存在'
            }), 404
    except Exception as e:
        logger.error(f"Failed to invalidate artwork {artwork_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@artwork_api.route(
    '/artworks/by-illust/<int:illust_id>/invalidate',
    methods=['PATCH']
)
@login_required
def invalidate_artwork_by_illust_id(illust_id):
    """批量标记某作品的所有页为废弃."""
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()

        if not reason:
            reason = 'Not like'

        count = services.artwork.mark_illust_invalid(illust_id, reason)
        if count > 0:
            return jsonify({
                'success': True,
                'message': f'已标记{count}张图片为废弃'
            })
        else:
            return jsonify({
                'success': False,
                'message': '作品不存在'
            }), 404
    except Exception as e:
        logger.error(
            f"Failed to invalidate artworks "
            f"by illust_id {illust_id}: {e}"
        )
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@artwork_api.route('/artworks/<int:artwork_id>/restore', methods=['PATCH'])
@login_required
def restore_artwork(artwork_id):
    """手动还原作品为有效."""
    try:
        success = services.artwork.restore_page(artwork_id)
        if success:
            return jsonify({
                'success': True,
                'message': '已还原为有效'
            })
        else:
            return jsonify({
                'success': False,
                'message': '作品不存在'
            }), 404
    except Exception as e:
        logger.error(f"Failed to restore artwork {artwork_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@artwork_api.route(
    '/artworks/by-illust/<int:illust_id>/restore',
    methods=['PATCH']
)
@login_required
def restore_artwork_by_illust_id(illust_id):
    """批量还原某作品的所有页为有效."""
    try:
        count = services.artwork.restore_illust(illust_id)
        if count > 0:
            return jsonify({
                'success': True,
                'message': f'已还原{count}张图片'
            })
        else:
            return jsonify({
                'success': False,
                'message': '作品不存在'
            }), 404
    except Exception as e:
        logger.error(
            f"Failed to restore artworks "
            f"by illust_id {illust_id}: {e}"
        )
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500
