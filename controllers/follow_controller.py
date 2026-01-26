"""关注控制器."""
import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

from services import services

logger = logging.getLogger(__name__)

follow_api = Blueprint('follow_api', __name__)


@follow_api.route('/follows', methods=['GET'])
@login_required
def get_follows():
    """获取关注用户列表."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    username = request.args.get('username', '', type=str)

    # 参数验证
    per_page = min(max(per_page, 1), 100)

    # 调用Service
    pagination = services.follow.paginate_follows(
        page=page,
        per_page=per_page,
        username_filter=username if username else None
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'follows': [follow.to_dict() for follow in pagination.items]
    })


@follow_api.route('/follows/stats', methods=['GET'])
@login_required
def get_follow_stats():
    """获取关注统计信息."""
    stats = services.follow.get_stats()
    active_users = services.follow.get_active_users(limit=10)

    return jsonify({
        'success': True,
        'stats': stats,
        'active_users': active_users
    })


@follow_api.route('/follows/batch', methods=['POST'])
@login_required
def batch_create_follows():
    """批量添加关注用户."""
    data = request.get_json()
    follows_data = data.get('follows', [])

    if not follows_data:
        return jsonify({
            'success': False,
            'message': 'No follows provided'
        }), 400

    try:
        count = services.follow.batch_create(follows_data)
        return jsonify({
            'success': True,
            'message': f'成功添加 {count} 个关注',
            'count': count
        })
    except Exception as e:
        logger.error(f"Failed to create follows: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500
