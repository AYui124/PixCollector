"""认证控制器."""
from flask import Blueprint, current_app, jsonify

from services import services

auth_api = Blueprint('auth_api', __name__)


@auth_api.route('/init/check', methods=['GET'])
def check_init():
    """检查系统是否已初始化."""
    is_initialized = services.auth.has_users()
    return jsonify({'initialized': is_initialized})


@auth_api.route('/init', methods=['POST'])
def init_system():
    """初始化系统，创建管理员账户."""
    if services.auth.has_users():
        return jsonify({
            'success': False,
            'message': 'System already initialized'
        }), 400

    username = current_app.config.get("ADMIN_USER", 'user')
    password = current_app.config.get("ADMIN_PWD", 'Pix@1234')

    if not password or len(password) < 6:
        return jsonify({
            'success': False,
            'message': 'Password must be at least 6 characters'
        }), 400

    # 创建管理员
    services.auth.create_admin_user(username, password)

    return jsonify({
        'success': True,
        'message': 'System initialized successfully'
    })
