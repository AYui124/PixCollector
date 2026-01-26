"""关注Service."""
from typing import ClassVar

from repositories.follow_repository import FollowRepository
from utils.pagination import Pagination


class FollowService:
    """关注业务逻辑层."""

    _instance: ClassVar['FollowService | None'] = None

    def __init__(self, follow_repo: FollowRepository):
        """
        初始化Service.

        Args:
            follow_repo: 关注Repository
        """
        self.follow_repo = follow_repo

    @classmethod
    def get_instance(cls) -> 'FollowService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            FollowService实例
        """
        if cls._instance is None:
            follow_repo = FollowRepository.get_instance()
            cls._instance = cls(follow_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_active_users(self, limit: int = 10) -> list[dict]:
        """
        获取最活跃用户列表.

        Args:
            limit: 限制返回数量

        Returns:
            用户字典列表
        """
        follows = self.follow_repo.get_active_users(limit)
        return [follow.to_dict() for follow in follows]

    def get_stats(self) -> dict[str, int]:
        """获取关注统计."""
        return self.follow_repo.get_stats()

    def paginate_follows(
        self,
        page: int = 1,
        per_page: int = 20,
        username_filter: str | None = None
    ) -> Pagination:
        """
        分页获取关注用户.

        Args:
            page: 页码
            per_page: 每页数量
            username_filter: 用户名过滤

        Returns:
            分页结果
        """
        return self.follow_repo.search_follows(
            page=page,
            per_page=per_page,
            username_filter=username_filter
        )

    def batch_create(self, follows_data: list[dict]) -> int:
        """
        批量创建关注.

        Args:
            follows_data: 关注数据列表

        Returns:
            实际创建的数量
        """
        return self.follow_repo.batch_create(follows_data)

    def get_by_user_id(self, user_id: int):
        """
        根据user_id获取关注.

        Args:
            user_id: 用户ID

        Returns:
            关注实例或None
        """
        return self.follow_repo.get_by_user_id(user_id)
