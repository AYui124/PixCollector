"""API密钥服务."""
from typing import ClassVar

from models.api_key import ApiKey
from repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    """API密钥业务逻辑."""

    _instance: ClassVar['ApiKeyService | None'] = None

    def __init__(self, api_key_repo: ApiKeyRepository):
        """
        初始化API密钥服务.

        Args:
            api_key_repo: API密钥Repository
        """
        self._api_key_repo = api_key_repo

    @classmethod
    def get_instance(cls) -> 'ApiKeyService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ApiKeyService实例
        """
        if cls._instance is None:
            api_key_repo = ApiKeyRepository.get_instance()
            cls._instance = cls(api_key_repo)
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
        return self._api_key_repo.get_by_key(key)

    def get_all(self) -> list[ApiKey]:
        """
        获取所有API密钥.

        Returns:
            ApiKey实例列表
        """
        return self._api_key_repo.get_all()

    def create(self, name: str) -> ApiKey:
        """
        创建API密钥.

        Args:
            name: 密钥名称

        Returns:
            创建的ApiKey实例
        """
        key = ApiKey.generate_key()
        return self._api_key_repo.create(
            key=key,
            name=name,
            is_active=True
        )

    def delete(self, key_id: int) -> bool:
        """
        删除API密钥.

        Args:
            key_id: API密钥ID

        Returns:
            是否删除成功
        """
        return self._api_key_repo.delete(key_id)

    def toggle_status(self, key_id: int) -> ApiKey | None:
        """
        切换API密钥状态.

        Args:
            key_id: API密钥ID

        Returns:
            更新后的ApiKey实例或None
        """
        return self._api_key_repo.toggle_status(key_id)

    def update_usage(self, key: str) -> None:
        """
        更新API密钥使用统计.

        Args:
            key: API密钥字符串
        """
        self._api_key_repo.update_usage(key)