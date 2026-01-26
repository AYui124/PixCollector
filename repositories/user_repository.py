"""用户Repository."""
from typing import ClassVar

from sqlalchemy import select

from models.user import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户数据访问层."""

    _instance: ClassVar['UserRepository | None'] = None

    def __init__(self):
        super().__init__(User)

    @classmethod
    def get_instance(cls) -> 'UserRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            UserRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_username(self, username: str) -> User | None:
        """
        根据用户名获取用户.

        Args:
            username: 用户名

        Returns:
            用户实例或None
        """
        with self.get_session() as session:
            user: User | None = session.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()
            return user

    def get_by_id(self, id: int) -> User | None:
        """
        根据ID获取用户.

        Args:
            id: 用户ID

        Returns:
            用户实例或None
        """
        with self.get_session() as session:
            user: User | None = session.execute(
                select(User).where(User.id == id)
            ).scalar_one_or_none()
            return user
