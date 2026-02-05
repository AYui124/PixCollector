"""关注Repository（SQLAlchemy 2.0）."""
from datetime import datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import delete, func, select

from models.follow import Follow
from repositories.base_repository import BaseRepository
from utils.pagination import Pagination


class FollowRepository(BaseRepository[Follow]):
    """关注数据访问层."""

    _instance: ClassVar['FollowRepository | None'] = None

    def __init__(self):
        super().__init__(Follow)

    @classmethod
    def get_instance(cls) -> 'FollowRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            FollowRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_user_id(self, user_id: int) -> Follow | None:
        """
        根据用户ID获取关注记录.

        Args:
            user_id: 用户ID

        Returns:
            关注实例或None
        """
        with self.get_session() as session:
            follow: Follow | None = session.execute(
                select(Follow).where(Follow.user_id == user_id)
            ).scalar_one_or_none()
            return follow

    def search_follows(
        self,
        page: int = 1,
        per_page: int = 20,
        username_filter: str | None = None
    ) -> Pagination:
        """
        搜索关注用户.

        Args:
            page: 页码
            per_page: 每页数量
            username_filter: 用户名过滤

        Returns:
            分页结果
        """
        with self.get_session() as session:
            query = select(Follow)

            if username_filter:
                query = query.filter(
                    Follow.user_name.like(f'%{username_filter}%')
                )

            query = query.order_by(Follow.created_at.desc())

            # 获取总数
            total_query = select(func.count()).select_from(query.subquery())
            total = session.execute(total_query).scalar() or 0

            # 分页
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            items = session.execute(query).scalars().all()

            return Pagination(list(items), total, page, per_page)

    def get_active_follows(self) -> list[Follow]:
        """
        获取有作品发布的关注用户.

        Returns:
            关注实例列表
        """
        with self.get_session() as session:
            query = select(Follow).filter(
                    Follow.last_artwork_date.is_not(None)
                )
            result = session.execute(query).scalars().all()
            return list(result)

    def get_active_users(self, limit: int = 10) -> list[Follow]:
        """
        获取最活跃用户（按last_artwork_date降序）.

        Args:
            limit: 限制返回数量

        Returns:
            关注实例列表
        """
        with self.get_session() as session:
            query = select(Follow).filter(
                Follow.last_artwork_date.is_not(None)
            ).order_by(
                Follow.last_artwork_date.desc()
            ).limit(limit)

            result = session.execute(query).scalars().all()
            return list(result)

    def get_by_all(self, limit: int | None = None) -> list[Follow]:
        """
        获取所有关注用户.

        Args:
            limit: 限制返回数量

        Returns:
            关注实例列表
        """
        with self.get_session() as session:
            query = select(Follow)
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def get_stats(self) -> dict[str, Any]:
        """获取关注统计."""

        seven_days_ago = datetime.now() - timedelta(days=7)
        thirty_days_ago = datetime.now() - timedelta(days=30)

        with self.get_session() as session:
            # 总关注用户数
            total_follows = session.execute(
                select(func.count()).select_from(Follow)
            ).scalar()

            # 有作品发布的用户数
            users_with_artworks = session.execute(
                select(func.count()).select_from(
                    select(Follow).filter(
                        Follow.last_artwork_date.is_not(None)
                    ).subquery()
                )
            ).scalar()

            # 最近7天发布作品的用户数
            active_users_last_7days = session.execute(
                select(func.count()).select_from(
                    select(Follow).filter(
                        Follow.last_artwork_date >= seven_days_ago
                    ).subquery()
                )
            ).scalar()

            # 最近30天发布作品的用户数
            active_users_last_30days = session.execute(
                select(func.count()).select_from(
                    select(Follow).filter(
                        Follow.last_artwork_date >= thirty_days_ago
                    ).subquery()
                )
            ).scalar()

            return {
                'total_follows': total_follows,
                'users_with_artworks': users_with_artworks,
                'active_users_last_7days': active_users_last_7days,
                'active_users_last_30days': active_users_last_30days
            }

    def update_last_artwork_date(
        self, user_id: int, post_date: Any
    ) -> Follow | None:
        """
        更新最后作品发布时间.

        Args:
            user_id: 用户ID
            post_date: 发布时间

        Returns:
            更新后的关注实例或None
        """
        with self.get_session() as session:
            instance: Follow | None = session.execute(
                select(Follow).where(Follow.user_id == user_id)
            ).scalar_one_or_none()

            if instance:
                instance.last_artwork_date = post_date
                session.flush()
                return instance
            return None

    def update_collect_dates(
        self,
        user_id: int,
        last_collect_date: datetime,
        first_collect_date: datetime | None = None
    ) -> Follow | None:
        """
        更新采集时间字段.

        Args:
            user_id: 用户ID
            last_collect_date: 最后采集时间
            first_collect_date: 首次采集时间（可选，如果提供则更新）

        Returns:
            更新后的关注实例或None
        """
        with self.get_session() as session:
            instance: Follow | None = session.execute(
                select(Follow).where(Follow.user_id == user_id)
            ).scalar_one_or_none()

            if instance:
                instance.last_collect_date = last_collect_date
                if first_collect_date:
                    instance.first_collect_date = first_collect_date
                session.flush()
                return instance
            return None

    def batch_create(self, follows_data: list[dict]) -> int:
        """
        批量创建关注.

        Args:
            follows_data: 关注数据列表

        Returns:
            实际创建的数量
        """
        created_count = 0
        with self.get_session() as session:
            for data in follows_data:
                user_id = data['user_id']

                # 去重检查
                existing = session.execute(
                    select(Follow).where(Follow.user_id == user_id)
                ).scalar_one_or_none()

                if not existing:
                    follow = Follow(**data)
                    session.add(follow)
                    created_count += 1

            return created_count

    def delete_by_user_id(self, user_id: int) -> bool:
        """
        根据用户ID删除关注.

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        with self.get_session() as session:
            # 检查是否存在
            follow = session.execute(
                select(Follow).where(Follow.user_id == user_id)
            ).scalar_one_or_none()

            if not follow:
                return False

            # 执行删除
            session.execute(
                delete(Follow).where(Follow.user_id == user_id)
            )

            return True
