"""作品Service."""
from typing import Any, ClassVar

from models.artwork import Artwork
from repositories.artwork_repository import ArtworkRepository
from utils.pagination import Pagination


class ArtworkService:
    """作品业务逻辑层."""

    _instance: ClassVar['ArtworkService | None'] = None

    def __init__(self, artwork_repo: ArtworkRepository):
        """
        初始化Service.

        Args:
            artwork_repo: 作品Repository
        """
        self.artwork_repo = artwork_repo

    @classmethod
    def get_instance(cls) -> 'ArtworkService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ArtworkService实例
        """
        if cls._instance is None:
            artwork_repo = ArtworkRepository.get_instance()
            cls._instance = cls(artwork_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_artworks_by_illust_id(
        self, illust_id: int
    ) -> list[Artwork]:
        """
        根据illust_id获取所有页.

        Args:
            illust_id: 作品ID

        Returns:
            作品实例列表
        """
        return self.artwork_repo.get_by_illust_id(illust_id)

    def get_stats(self) -> dict[str, int]:
        """获取统计信息."""
        total = self.artwork_repo.count()
        valid = self.artwork_repo.count_valid()
        invalid = total - valid
        r18 = self.artwork_repo.count_r18()

        return {
            'total_artworks': total,
            'valid_artworks': valid,
            'invalid_artworks': invalid,
            'r18_artworks': r18
        }

    def paginate_artworks(
        self,
        page: int = 1,
        per_page: int = 20,
        type_filter: str | None = None,
        collect_type_filter: str | None = None,
        is_r18_filter: bool | None = None,
        author_name_filter: str | None = None,
        is_valid_filter: bool | None = None,
        post_date_start: Any | None = None,
        post_date_end: Any | None = None,
        tags_filter: str | None = None,
        tags_match: str = 'or',
        illust_id_filter: int | None = None
    ) -> Pagination:
        """
        分页获取作品.

        Args:
            page: 页码
            per_page: 每页数量
            type_filter: 类型过滤
            collect_type_filter: 采集类型过滤
            is_r18_filter: R18过滤
            author_name_filter: 作者名过滤
            is_valid_filter: 有效状态过滤
            post_date_start: 发布开始日期
            post_date_end: 发布结束日期
            tags_filter: 标签过滤（逗号分隔）
            tags_match: 标签匹配方式（or/and）
            illust_id_filter: 作品ID过滤

        Returns:
            分页结果
        """
        return self.artwork_repo.search_artworks(
            page=page,
            per_page=per_page,
            type_filter=type_filter,
            collect_type_filter=collect_type_filter,
            is_r18_filter=is_r18_filter,
            author_name_filter=author_name_filter,
            is_valid_filter=is_valid_filter,
            post_date_start=post_date_start,
            post_date_end=post_date_end,
            tags_filter=tags_filter,
            tags_match=tags_match,
            illust_id_filter=illust_id_filter
        )

    def get_random_artworks(
        self,
        limit: int = 10,
        is_r18: bool | None = None,
        tags_filter: str | None = None,
        tags_match: str = 'or'
    ) -> list[dict]:
        """
        获取随机作品（用于公开API）.

        Args:
            limit: 数量
            is_r18: R18过滤
            tags_filter: 标签过滤（逗号分隔）
            tags_match: 标签匹配方式（or/and）

        Returns:
            作品字典列表
        """
        artworks = self.artwork_repo.get_random_artworks(
            limit=limit,
            is_r18=is_r18,
            tags_filter=tags_filter,
            tags_match=tags_match
        )

        return [
            {
                'illust_id': artwork.illust_id,
                'title': artwork.title,
                'author_id': artwork.author_id,
                'author_name': artwork.author_name,
                'url': artwork.url,
                'share_url': artwork.share_url,
                'page': f'{artwork.page_index + 1} / {artwork.page_count}',
                'total_bookmarks': artwork.total_bookmarks,
                'total_view': artwork.total_view,
                'tags': artwork.tags if isinstance(artwork.tags, list) else [],
                'type': artwork.type,
                'is_r18': artwork.is_r18
            }
            for artwork in artworks
        ]

    def mark_invalid(
        self, artwork_id: int, reason: str
    ) -> bool:
        """
        标记作品为失效.

        Args:
            artwork_id: 作品ID
            reason: 失效原因

        Returns:
            是否成功
        """
        result = self.artwork_repo.mark_invalid(artwork_id, reason)
        return result is not None

    def mark_invalid_by_illust_id(
        self, illust_id: int, reason: str
    ) -> int:
        """
        标记某个作品的所有页为失效.

        Args:
            illust_id: 作品ID
            reason: 失效原因

        Returns:
            更新的作品数量
        """
        return self.artwork_repo.mark_invalid_by_illust_id(illust_id, reason)

    def get_dashboard_stats(self) -> dict[str, int]:
        """
        获取dashboard统计信息.

        Returns:
            统计字典
        """
        # artwork统计
        total = self.artwork_repo.count()
        valid = self.artwork_repo.count_valid()
        invalid = total - valid

        # 今日统计
        today_stats = self.artwork_repo.get_today_stats()

        return {
            'total_artworks': total,
            'valid_artworks': valid,
            'invalid_artworks': invalid,
            'today_artworks': today_stats['today_artworks'],
            'today_updates': today_stats['today_updates']
        }

    def batch_create(self, artworks_data: list[dict]) -> int:
        """
        批量创建作品.

        Args:
            artworks_data: 作品数据列表

        Returns:
            实际创建的数量
        """
        return self.artwork_repo.batch_create(artworks_data)

    def count_valid(self) -> int:
        """
        统计有效作品数.

        Returns:
            有效作品数量
        """
        return self.artwork_repo.count_valid()

    def count_r18(self) -> int:
        """
        统计R18作品数.

        Returns:
            R18作品数量
        """
        return self.artwork_repo.count_r18()

    def search_artworks_raw(self, **kwargs) -> list:
        """
        获取原始作品列表（用于统计）.

        Args:
            **kwargs: 查询参数

        Returns:
            作品列表
        """
        pagination = self.artwork_repo.search_artworks(**kwargs)
        return pagination.items
