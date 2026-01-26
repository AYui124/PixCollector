"""Web认证服务."""
from typing import ClassVar

from models.user import User
from repositories.user_repository import UserRepository


class AuthService:
    """Web认证业务逻辑."""

    _instance: ClassVar['AuthService | None'] = None

    def __init__(self, user_repo: UserRepository):
        """
        初始化认证服务.

        Args:
            user_repo: 用户Repository
        """
        self._user_repo = user_repo

    @classmethod
    def get_instance(cls) -> 'AuthService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            AuthService实例
        """
        if cls._instance is None:
            user_repo = UserRepository.get_instance()
            cls._instance = cls(user_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def authenticate(
        self, username: str, password: str
    ) -> User | None:
        """
        验证用户登录.

        Args:
            username: 用户名
            password: 密码

        Returns:
            用户实例或None
        """
        user = self._user_repo.get_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def get_user_by_id(self, user_id: int) -> User | None:
        """
        根据ID获取用户.

        Args:
            user_id: 用户ID

        Returns:
            用户实例或None
        """
        return self._user_repo.get_by_id(user_id)

    def create_admin_user(
        self, username: str, password: str
    ) -> User:
        """
        创建管理员用户.

        Args:
            username: 用户名
            password: 密码

        Returns:
            创建的用户实例
        """
        user = User(
            id=None,
            username=username,
            password_hash='',
            is_admin=True
        )
        user.set_password(password)
        return self._user_repo.create(
            username=user.username,
            password_hash=user.password_hash,
            is_admin=user.is_admin,
            created_at=user.created_at
        )

    def has_users(self) -> bool:
        """检查是否有用户."""
        return self._user_repo.count() > 0
