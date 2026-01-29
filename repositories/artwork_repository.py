"""作品Repository（SQLAlchemy 2.0）."""
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import delete, func, or_, select

from models.artwork import Artwork
from repositories.base_repository import BaseRepository
from utils.pagination import Pagination
from utils.time_utils import get_utc_now


class ArtworkRepository(BaseRepository[Artwork]):
    """作品数据访问层."""

    _instance: ClassVar['ArtworkRepository | None'] = None

    def __init__(self):
        super().__init__(Artwork)

    @classmethod
    def get_instance(cls) -> 'ArtworkRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ArtworkRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_illust_id_and_page(
        self, illust_id: int, page_index: int
    ) -> Artwork | None:
        """
        根据illust_id和page_index获取作品.

        Args:
            illust_id: 作品ID
            page_index: 页面索引

        Returns:
            作品实例或None
        """
        with self.get_session() as session:
            artwork: Artwork | None = session.execute(
                select(Artwork).where(
                    Artwork.illust_id == illust_id,
                    Artwork.page_index == page_index
                )
            ).scalar_one_or_none()
            return artwork

    def get_by_illust_id(self, illust_id: int) -> list[Artwork]:
        """
        根据illust_id获取所有页.

        Args:
            illust_id: 作品ID

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(Artwork.illust_id == illust_id)
            return list(session.execute(query).scalars().all())

    def get_by_author_id(
        self, author_id: int, limit: int | None = None
    ) -> list[Artwork]:
        """
        根据作者ID获取作品.

        Args:
            author_id: 作者ID
            limit: 限制返回数量

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(Artwork.author_id == author_id)
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def get_valid_artworks(
        self, limit: int | None = None
    ) -> list[Artwork]:
        """
        获取有效作品.

        Args:
            limit: 限制返回数量

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(Artwork.is_valid)
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def get_r18_artworks(
        self, limit: int | None = None
    ) -> list[Artwork]:
        """
        获取R18作品.

        Args:
            limit: 限制返回数量

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(
                Artwork.is_r18, Artwork.is_valid
            )
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def count_valid(self) -> int:
        """统计有效作品数量."""
        with self.get_session() as session:
            result = session.execute(
                select(func.count()).select_from(
                    select(Artwork).where(Artwork.is_valid).subquery()
                )
            ).scalar()
            return result or 0

    def count_r18(self) -> int:
        """统计R18作品数量."""
        with self.get_session() as session:
            result = session.execute(
                select(func.count()).select_from(
                    select(Artwork).where(
                        Artwork.is_r18, Artwork.is_valid
                    ).subquery()
                )
            ).scalar()
            return result or 0

    def search_artworks(
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
        搜索作品（支持多条件过滤）.

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
        with self.get_session() as session:
            query = select(Artwork)

            # 类型过滤
            if type_filter:
                query = query.filter(Artwork.type == type_filter)

            # 采集类型过滤
            if collect_type_filter:
                query = query.filter(
                    Artwork.collect_type == collect_type_filter
                )

            # R18过滤
            if is_r18_filter is not None:
                query = query.filter(Artwork.is_r18 == is_r18_filter)

            # 作品ID筛选
            if illust_id_filter:
                query = query.filter(Artwork.illust_id == illust_id_filter)

            # 作者名筛选
            if author_name_filter:
                query = query.filter(
                    Artwork.author_name.like(f'%{author_name_filter}%')
                )

            # 有效状态筛选
            if is_valid_filter is not None:
                query = query.filter(Artwork.is_valid == is_valid_filter)

            # 发布时间范围筛选
            if post_date_start:
                query = query.filter(Artwork.post_date >= post_date_start)

            if post_date_end:
                query = query.filter(Artwork.post_date <= post_date_end)

            # 标签过滤
            if tags_filter:
                tags_list = [
                    tag.strip()
                    for tag in tags_filter.split(',') if tag.strip()
                ]
                if tags_list:
                    if tags_match.lower() == 'and':
                        # AND模式：所有标签都必须匹配
                        for tag in tags_list:
                            query = query.filter(
                                Artwork.tags.like(f'%{tag}%')
                            )
                    else:
                        # OR模式：任一标签匹配即可
                        or_conditions = [
                            Artwork.tags.like(f'%{tag}%') for tag in tags_list
                        ]
                        query = query.filter(or_(*or_conditions))

            # 先获取总数
            total_query = select(func.count()).select_from(query.subquery())
            total = session.execute(total_query).scalar() or 0

            # 分页
            offset = (page - 1) * per_page
            query = query.order_by(Artwork.post_date.desc())
            query = query.offset(offset).limit(per_page)

            items = session.execute(query).scalars().all()

            return Pagination(list(items), total, page, per_page)

    def get_random_artworks(
        self,
        limit: int = 10,
        is_r18: bool | None = None,
        tags_filter: str | None = None,
        tags_match: str = 'or'
    ) -> list[Artwork]:
        """
        获取随机作品.

        Args:
            limit: 数量
            is_r18: R18过滤
            tags_filter: 标签过滤（逗号分隔）
            tags_match: 标签匹配方式（or/and）

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(
                Artwork.is_valid,
                Artwork.type == 'illust'
            )

            if is_r18 is not None:
                query = query.where(Artwork.is_r18 == is_r18)

            # 标签过滤
            if tags_filter:
                tags_list = [
                    tag.strip()
                    for tag in tags_filter.split(',') if tag.strip()
                ]
                if tags_list:
                    if tags_match.lower() == 'and':
                        # AND模式：所有标签都必须匹配
                        for tag in tags_list:
                            query = query.filter(
                                Artwork.tags.like(f'%{tag}%')
                            )
                    else:
                        # OR模式：任一标签匹配即可
                        or_conditions = [
                            Artwork.tags.like(f'%{tag}%') for tag in tags_list
                        ]
                        query = query.filter(or_(*or_conditions))

            query = query.order_by(func.random()).limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def get_today_stats(self) -> dict[str, int]:
        """获取今日统计."""

        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        with self.get_session() as session:
            today_artworks = session.execute(
                select(func.count()).select_from(
                    select(Artwork).filter(
                        Artwork.created_at >= start_of_day
                    ).subquery()
                )
            ).scalar() or 0

            today_updates = session.execute(
                select(func.count()).select_from(
                    select(Artwork).filter(
                        Artwork.last_updated_at >= start_of_day
                    ).subquery()
                )
            ).scalar() or 0

            return {
                'today_artworks': today_artworks,
                'today_updates': today_updates
            }

    def mark_page_invalid(
        self, artwork_id: int, reason: str
    ) -> Artwork | None:
        """
        标记作品为失效.

        Args:
            artwork_id: 作品ID
            reason: 失效原因

        Returns:
            更新后的作品实例或None
        """
        return self.update(
            artwork_id,
            is_valid=False,
            error_message=reason
        )

    def mark_illust_invalid(
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
        with self.get_session() as session:
            artworks = session.execute(
                select(Artwork).where(Artwork.illust_id == illust_id)
            ).scalars().all()

            count = 0
            for artwork in artworks:
                artwork.is_valid = False
                artwork.error_message = reason
                count += 1

            return count

    def delete_by_illust_id(self, illust_id: int) -> int:
        """
        删除某个作品的所有页.

        Args:
            illust_id: 作品ID

        Returns:
            删除的作品数量
        """
        with self.get_session() as session:
            # 先获取要删除的数量
            query = select(func.count()).select_from(Artwork).where(
                Artwork.illust_id == illust_id
            )
            count = session.execute(query).scalar() or 0

            # 执行删除
            session.execute(
                delete(Artwork).where(Artwork.illust_id == illust_id)
            )

            return count

    def get_by_collect_type(
        self, collect_type: str, limit: int | None = None
    ) -> list[Artwork]:
        """
        根据采集类型获取作品.

        Args:
            collect_type: 采集类型
            limit: 限制返回数量

        Returns:
            作品实例列表
        """
        with self.get_session() as session:
            query = select(Artwork).where(Artwork.collect_type == collect_type)
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def batch_create(self, artworks_data: list[dict]) -> int:
        """
        批量创建作品.

        Args:
            artworks_data: 作品数据列表

        Returns:
            实际创建的数量
        """
        created_count = 0
        with self.get_session() as session:
            for data in artworks_data:
                illust_id = data['illust_id']
                page_index = data.get('page_index', 0)

                # 去重检查
                existing = session.execute(
                    select(Artwork).where(
                        Artwork.illust_id == illust_id,
                        Artwork.page_index == page_index
                    )
                ).scalar_one_or_none()

                if not existing:
                    artwork = Artwork(**data)
                    session.add(artwork)
                    created_count += 1

            return created_count

    def get_artworks_for_update(
        self,
        post_date_start: datetime,
        per_page: int = 200
    ) -> list[Artwork]:
        """
        获取需要更新的作品（有效，按last_updated_at升序）.

        Args:
            post_date_start: 发布开始日期
            per_page: 每次处理数量

        Returns:
            作品实例列表
        """
        update_date = get_utc_now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        with self.get_session() as session:
            query = select(Artwork).where(
                Artwork.is_valid,
                Artwork.post_date >= post_date_start,
                Artwork.last_updated_at < update_date
            ).order_by(
                Artwork.last_updated_at.asc()
            ).limit(per_page)

            return list(session.execute(query).scalars().all())
