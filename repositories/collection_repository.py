"""采集日志Repository（SQLAlchemy 2.0）."""
from datetime import datetime, timedelta
from typing import ClassVar

from sqlalchemy import func, select

from models.collection_log import CollectionLog
from repositories.base_repository import BaseRepository
from utils.pagination import Pagination


class CollectionRepository(BaseRepository[CollectionLog]):
    """采集日志数据访问层."""

    _instance: ClassVar['CollectionRepository | None'] = None

    def __init__(self):
        super().__init__(CollectionLog)

    @classmethod
    def get_instance(cls) -> 'CollectionRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            CollectionRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_recent(self, limit: int = 10) -> list[CollectionLog]:
        """
        获取最近的日志.

        Args:
            limit: 限制返回数量

        Returns:
            日志实例列表
        """
        with self.get_session() as session:
            query = select(CollectionLog).order_by(
                CollectionLog.created_at.desc()
            ).limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def get_by_type(
        self, log_type: str, limit: int | None = None
    ) -> list[CollectionLog]:
        """
        根据类型获取日志.

        Args:
            log_type: 日志类型
            limit: 限制返回数量

        Returns:
            日志实例列表
        """
        with self.get_session() as session:
            query = select(CollectionLog).where(
                CollectionLog.log_type == log_type
            )
            query = query.order_by(CollectionLog.created_at.desc())
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def create_log(
        self, log_type: str, status: str, message: str,
        artworks_count: int = 0
    ) -> CollectionLog:
        """
        创建采集日志.

        Args:
            log_type: 日志类型
            status: 状态
            message: 消息
            artworks_count: 作品数量

        Returns:
            日志实例
        """
        return super().create(
            log_type=log_type,
            status=status,
            message=message,
            artworks_count=artworks_count
        )

    def update_success(
        self, log_id: int, message: str, artworks_count: int = 0
    ) -> CollectionLog | None:
        """
        更新日志为成功状态.

        Args:
            log_id: 日志ID
            message: 消息
            artworks_count: 作品数量

        Returns:
            更新后的日志实例或None
        """
        return self.update(
            log_id,
            status='success',
            message=message,
            artworks_count=artworks_count
        )

    def update_error(self, log_id: int, message: str) -> CollectionLog | None:
        """
        更新日志为失败状态.

        Args:
            log_id: 日志ID
            message: 错误消息

        Returns:
            更新后的日志实例或None
        """
        return self.update(
            log_id,
            status='failed',
            message=message
        )

    def delete_old_logs(self, days: int) -> int:
        """
        删除旧日志.

        Args:
            days: 保留天数

        Returns:
            删除的数量
        """

        cutoff_date = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            result = session.execute(
                select(CollectionLog).filter(
                    CollectionLog.created_at < cutoff_date
                )
            ).scalars().all()

            count = len(result)
            for log in result:
                session.delete(log)

            return count

    def get_logs_page(
        self,
        page: int = 1,
        per_page: int = 20,
        log_type_filter: str | None = None,
        status_filter: str | None = None
    ) -> Pagination:
        """
        分页获取日志.

        Args:
            page: 页码
            per_page: 每页数量
            log_type_filter: 日志类型过滤
            status_filter: 状态过滤

        Returns:
            分页结果
        """

        with self.get_session() as session:
            query = select(CollectionLog)

            if log_type_filter:
                query = query.filter(CollectionLog.log_type == log_type_filter)

            if status_filter:
                query = query.filter(CollectionLog.status == status_filter)

            query = query.order_by(CollectionLog.created_at.desc())

            # 获取总数
            total_query = select(func.count()).select_from(query.subquery())
            total = session.execute(total_query).scalar() or 0

            # 分页
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            items = session.execute(query).scalars().all()

            return Pagination(list(items), total, page, per_page)
