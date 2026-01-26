"""采集日志Service."""
from typing import ClassVar

from repositories.collection_repository import CollectionRepository


class CollectionService:
    """采集日志业务逻辑层."""

    _instance: ClassVar['CollectionService | None'] = None

    def __init__(self, collection_repo: CollectionRepository):
        """
        初始化Service.

        Args:
            collection_repo: 采集日志Repository
        """
        self._collection_repo = collection_repo

    @classmethod
    def get_instance(cls) -> 'CollectionService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            CollectionService实例
        """
        if cls._instance is None:
            collection_repo = CollectionRepository.get_instance()
            cls._instance = cls(collection_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_recent_logs(self, limit: int = 100) -> list:
        """
        获取最近的采集日志.

        Args:
            limit: 限制返回数量

        Returns:
            日志实例列表
        """
        return self._collection_repo.get_recent(limit)

    def get_logs_by_type(
        self, log_type: str, limit: int | None = None
    ) -> list:
        """
        根据类型获取日志.

        Args:
            log_type: 日志类型
            limit: 限制返回数量

        Returns:
            日志实例列表
        """
        return self._collection_repo.get_by_type(log_type, limit)