"""API密钥Repository."""
from typing import ClassVar

from sqlalchemy import select

from models.api_key import ApiKey
from repositories.base_repository import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    """API密钥数据访问层."""

    _instance: ClassVar['ApiKeyRepository | None'] = None

    def __init__(self):
        super().__init__(ApiKey)

    @classmethod
    def get_instance(cls) -> 'ApiKeyRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ApiKeyRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_key(self, key: str) -> ApiKey | None:
        """
        根据密钥字符串获取API密钥.

        Args:
            key: API密钥字符串

        Returns:
            ApiKey实例或None
        """
        with self.get_session() as session:
            api_key: ApiKey | None = session.execute(
                select(ApiKey).where(ApiKey.key == key)
            ).scalar_one_or_none()
            return api_key

    def get_all(self) -> list[ApiKey]:
        """
        获取所有API密钥.

        Returns:
            ApiKey实例列表
        """
        with self.get_session() as session:
            api_keys: list[ApiKey] = session.execute(
                select(ApiKey).order_by(ApiKey.created_at.desc())
            ).scalars().all()
            return api_keys

    def update_usage(self, key: str) -> None:
        """
        更新API密钥使用统计.

        Args:
            key: API密钥字符串
        """
        with self.get_session() as session:
            api_key: ApiKey | None = session.execute(
                select(ApiKey).where(ApiKey.key == key)
            ).scalar_one_or_none()

            if api_key:
                api_key.update_usage()
                session.flush()

    def toggle_status(self, id: int) -> ApiKey | None:
        """
        切换API密钥状态.

        Args:
            id: API密钥ID

        Returns:
            更新后的ApiKey实例或None
        """
        with self.get_session() as session:
            api_key: ApiKey | None = session.execute(
                select(ApiKey).where(ApiKey.id == id)
            ).scalar_one_or_none()

            if api_key:
                api_key.is_active = not api_key.is_active
                session.flush()
                return api_key
            return None
