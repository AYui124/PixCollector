"""采集控制器."""
import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

from repositories.collection_repository import CollectionRepository
from services import huey_service, services

logger = logging.getLogger(__name__)

collect_api = Blueprint('collect_api', __name__)


@collect_api.route('/collect/daily', methods=['POST'])
@login_required
def collect_daily():
    """手动触发每日排行采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.collect_daily_rank_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '每日排行采集任务已提交'
        })
    except Exception as e:
        logger.error(f"Daily rank task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/weekly', methods=['POST'])
@login_required
def collect_weekly():
    """手动触发每周排行采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.collect_weekly_rank_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '每周排行采集任务已提交'
        })
    except Exception as e:
        logger.error(f"Weekly rank task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/monthly', methods=['POST'])
@login_required
def collect_monthly():
    """手动触发每月排行采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.collect_monthly_rank_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '每月排行采集任务已提交'
        })
    except Exception as e:
        logger.error(f"Monthly rank task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/sync-follows', methods=['POST'])
@login_required
def sync_follows():
    """手动触发关注列表同步."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.sync_follows_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '关注列表同步任务已提交'
        })
    except Exception as e:
        logger.error(f"Follow sync task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/status', methods=['GET'])
@login_required
def get_collect_status():
    """获取采集状态."""
    artwork_stats = services.artwork.get_stats()
    follow_stats = services.follow.get_stats()

    # 获取最新日志
    log_repo = CollectionRepository()
    recent_logs = log_repo.get_recent(10)

    return jsonify({
        'success': True,
        'stats': {
            **artwork_stats,
            **follow_stats
        },
        'recent_logs': [log.to_dict() for log in recent_logs]
    })


@collect_api.route('/collect/logs', methods=['GET'])
@login_required
def get_collect_logs():
    """获取采集日志（分页）."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    type_filter = request.args.get('type', '', type=str)
    status_filter = request.args.get('status', '', type=str)

    # 参数验证
    per_page = min(max(per_page, 1), 100)

    log_repo = CollectionRepository()
    pagination = log_repo.get_logs_page(
        page=page,
        per_page=per_page,
        log_type_filter=type_filter if type_filter else None,
        status_filter=status_filter if status_filter else None
    )

    return jsonify({
        'success': True,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'logs': [log.to_dict() for log in pagination.items]
    })


@collect_api.route('/collect/user-artworks', methods=['POST'])
@login_required
def collect_user_artworks():
    """手动触发单个用户作品采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'user_id is required'
        }), 400

    try:
        task = huey_service.collect_user_artworks_task(user_id)
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '用户作品采集任务已提交'
        })
    except Exception as e:
        logger.error(f"User artworks task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/follow-user-artworks', methods=['POST'])
@login_required
def collect_follow_user_artworks():
    """手动触发初始全量关注采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.collect_all_follow_artworks_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '初始全量关注采集任务已提交'
        })
    except Exception as e:
        logger.error(f"Follow artworks task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/follow-new-works', methods=['POST'])
@login_required
def collect_follow_new_works():
    """手动触发关注用户新作品采集."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.collect_follow_new_works_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '关注用户新作品采集任务已提交'
        })
    except Exception as e:
        logger.error(f"Follow new works task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/update-artworks', methods=['POST'])
@login_required
def update_artworks():
    """手动触发作品元数据更新."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.update_artworks_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '作品元数据更新任务已提交'
        })
    except Exception as e:
        logger.error(f"Artworks update task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/cleanup-logs', methods=['POST'])
@login_required
def cleanup_logs():
    """手动触发旧日志清理."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        task = huey_service.cleanup_logs_task()
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '旧日志清理任务已提交'
        })
    except Exception as e:
        logger.error(f"Logs cleanup task submission failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@collect_api.route('/collect/task/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """获取任务状态."""
    try:
        status = huey_service.get_task_status(task_id)
        return jsonify({'success': True, **status})
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
