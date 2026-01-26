"""Web认证模块（依赖Flask）."""
import logging

from flask_login import LoginManager, UserMixin

from services.auth_service import AuthService

logger = logging.getLogger(__name__)

# 全局实例
login_manager = LoginManager()

# Service引用（在app初始化时设置）
_auth_service: AuthService | None = None


def init_auth(app, auth_service: AuthService) -> None:
    """
    初始化认证系统.

    Args:
        app: Flask应用实例
        auth_service: 认证服务实例
    """
    global _auth_service
    _auth_service = auth_service

    login_manager.init_app(app)
    login_manager.login_view = 'web.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'


class WebUser(UserMixin):
    """Flask-Login用户代理."""

    def __init__(self, user_id: int, username: str, is_admin: bool = False):
        """
        初始化Web用户.

        Args:
            user_id: 用户ID
            is_admin: 是否管理员
        """
        self.id = user_id
        self.username = username
        self.is_admin = is_admin


@login_manager.user_loader
def load_user(user_id: int | str) -> WebUser | None:
    """
    加载用户.

    Args:
        user_id: 用户ID

    Returns:
        WebUser实例或None
    """
    if _auth_service is None:
        logger.error("AuthService not initialized")
        return None

    try:
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id
        user = _auth_service.get_user_by_id(user_id_int)

        if user:
            return WebUser(user.id, user.username, user.is_admin)

    except Exception as e:
        logger.error(f"Failed to load user {user_id}: {e}")

    return None
