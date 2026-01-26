"""公开API路由模块（无需登录）."""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request

from services import services

logger = logging.getLogger(__name__)

# 创建API蓝图
public_api = Blueprint('api', __name__)


@public_api.route('/public/stats', methods=['GET'])
def get_public_stats():
    """获取公开统计信息（无需登录）."""
    # 总作品数（过滤失效）
    total_artworks = services.artwork.count_valid()

    # R18作品数（过滤失效）
    r18_artworks = services.artwork.count_r18()

    # 非R18作品数（过滤失效）
    non_r18_artworks = total_artworks - r18_artworks

    # 最后采集时间
    last_artworks = services.artwork.search_artworks_raw(
        page=1, per_page=1
    )
    last_collect_time = None
    if last_artworks:
        last_collect_time = last_artworks[0].created_at.strftime(
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

        artworks = services.artwork.search_artworks_raw(
            page=1, per_page=1000
        )

        count = 0
        for artwork in artworks:
            if start_of_day <= artwork.created_at <= end_of_day:
                count += 1

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


@public_api.route('/public/random/artwork', methods=['GET'])
def get_random_artwork():
    """获取随机图片（公开API，支持标签过滤）."""
    limit = request.args.get('limit', 1, type=int)
    tags_param = request.args.get('tags', '')
    tags_match = request.args.get('tags_match', 'or', type=str)
    is_r18_param = request.args.get('is_r18', 'false', type=str)

    # 参数验证
    limit = min(max(limit, 1), 10)
    tags_match = tags_match.lower() if tags_match in ['and', 'or'] else 'or'

    # 转换参数
    is_r18_filter = None
    if is_r18_param.lower() == 'true':
        is_r18_filter = True
    elif is_r18_param.lower() == 'false':
        is_r18_filter = False

    tags_filter = tags_param if tags_param else None

    # 使用Service获取随机作品
    artworks_data = services.artwork.get_random_artworks(
        limit=limit,
        is_r18=is_r18_filter,
        tags_filter=tags_filter,
        tags_match=tags_match
    )

    if not artworks_data:
        return jsonify({
            'success': False,
            'message': '未找到符合条件的作品'
        })

    # 获取代理URL配置
    proxy_url = current_app.config.get('PIXIV_PROXY_URL', 'https://i.pixiv.re')

    # 替换URL为代理URL
    for artwork in artworks_data:
        artwork['url'] = artwork['url'].replace(
            'https://i.pximg.net', proxy_url
        )

    return jsonify({
        'success': True,
        'count': len(artworks_data),
        'artworks': artworks_data
    })


@public_api.route('/public/random/artwork/image', methods=['GET'])
def get_random_artwork_image():
    """获取随机图片的图片URL（公开API，支持标签过滤）."""
    tags_param = request.args.get('tags', '')
    tags_match = request.args.get('tags_match', 'or', type=str)
    is_r18_param = request.args.get('is_r18', 'all', type=str)

    # 转换参数
    is_r18_filter = None
    if is_r18_param.lower() == 'true':
        is_r18_filter = True
    elif is_r18_param.lower() == 'false':
        is_r18_filter = False

    tags_filter = tags_param if tags_param else None

    # 获取单个随机作品
    artworks_data = services.artwork.get_random_artworks(
        limit=1,
        is_r18=is_r18_filter,
        tags_filter=tags_filter,
        tags_match=tags_match
    )

    if not artworks_data:
        return jsonify({
            'success': False,
            'message': '未找到有效的作品'
        })

    artwork = artworks_data[0]

    # 获取代理URL配置
    proxy_url = current_app.config.get('PIXIV_PROXY_URL', 'https://i.pixiv.re')

    return jsonify({
        'success': True,
        'image_url': artwork['url'].replace('https://i.pximg.net', proxy_url),
        'illust_id': artwork['illust_id'],
        'title': artwork['title'],
        'author_name': artwork['author_name'],
        'tags': artwork['tags'],
        'is_r18': artwork['is_r18']
    })
