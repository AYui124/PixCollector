"""配置控制器."""
import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

from scheduler import task_scheduler
from services import services

logger = logging.getLogger(__name__)

config_api = Blueprint('config_api', __name__)


@config_api.route('/config/tokens', methods=['POST'])
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

    # 保存token
    services.config.save_tokens(access_token, refresh_token)

    # 重置 Pixiv service 以便重新初始化
    services.pixiv = None
    logger.info("Pixiv service will be reinitialized on next access")

    return jsonify({
        'success': True,
        'message': 'Tokens saved successfully'
    })


@config_api.route('/config/test', methods=['POST'])
@login_required
def test_connection():
    """测试Pixiv连接."""
    if not services.pixiv:
        return jsonify({
            'success': False,
            'message': 'Pixiv service not initialized'
        }), 500

    try:
        user_id = services.pixiv.client.user_id
        return jsonify({
            'success': True,
            'message': f'token检测成功 (user_id: {user_id})'
        })
    except Exception as e:
        logger.error(f"Token test failed: {e}")
        return jsonify({'success': False, 'message': 'token检测失败'}), 500


@config_api.route('/config', methods=['GET'])
@login_required
def get_config():
    """获取所有配置."""
    config_dict = services.config.get_all_config()

    from repositories.config_repository import ConfigRepository
    config_repo = ConfigRepository.get_instance()
    with config_repo.get_session() as session:
        from sqlalchemy import select

        from models.system_config import SystemConfig
        config_items = session.execute(
            select(SystemConfig)
        ).scalars().all()

    return jsonify({
        'success': True,
        'config': config_dict,
        'config_items': [item.to_dict() for item in config_items]
    })


@config_api.route('/config', methods=['POST'])
@login_required
def update_config():
    """更新系统配置."""
    data = request.get_json()
    services.config.batch_set_config(data)

    # 检查是否更新了速率限制配置，如果是则重置 Pixiv service
    rate_limit_keys = [
        'api_delay_min', 'api_delay_max',
        'error_delay_429_min', 'error_delay_429_max',
        'error_delay_403_min', 'error_delay_403_max',
        'error_delay_other_min', 'error_delay_other_max'
    ]
    if any(key in data for key in rate_limit_keys):
        services.pixiv = None
        logger.info("Pixiv service will be reinitialized on next access")

    return jsonify({
        'success': True,
        'message': 'Configuration updated successfully',
        'config': services.config.get_all_config()
    })


@config_api.route('/config/scheduler', methods=['GET'])
@login_required
def get_scheduler_config():
    """获取定时任务配置."""
    configs = services.scheduler.get_all_configs()

    return jsonify({
        'success': True,
        'configs': [config.to_dict() for config in configs]
    })


@config_api.route('/config/scheduler', methods=['POST'])
@login_required
def update_scheduler_config():
    """更新定时任务配置."""
    data = request.get_json()
    services.scheduler.update_configs(data)

    return jsonify({
        'success': True,
        'message': 'Scheduler configuration updated successfully'
    })


@config_api.route('/scheduler/refresh', methods=['POST'])
@login_required
def refresh_scheduler():
    """刷新调度器任务."""
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
