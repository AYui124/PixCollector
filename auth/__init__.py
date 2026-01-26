"""认证模块初始化."""
from auth.web_auth import WebUser, init_auth, login_manager

__all__ = ['login_manager', 'init_auth', 'WebUser']
