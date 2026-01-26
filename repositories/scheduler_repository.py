"""定时任务Repository（SQLAlchemy 2.0）."""
from datetime import datetime
from typing import ClassVar

from sqlalchemy import select

from models.scheduler_config import SchedulerConfig
from repositories.base_repository import BaseRepository


class SchedulerRepository(BaseRepository[SchedulerConfig]):
    """定时任务配置数据访问层."""

    _instance: ClassVar['SchedulerRepository | None'] = None

    def __init__(self):
        super().__init__(SchedulerConfig)

    @classmethod
    def get_instance(cls) -> 'SchedulerRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            SchedulerRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_type(
        self, collect_type: str
    ) -> SchedulerConfig | None:
        """
        根据采集类型获取配置.

        Args:
            collect_type: 采集类型

        Returns:
            配置实例或None
        """
        with self.get_session() as session:
            return session.execute(
                select(SchedulerConfig).where(
                    SchedulerConfig.collect_type == collect_type
                )
            ).scalar_one_or_none()

    def get_all(self, limit: int | None = None) -> list[SchedulerConfig]:
        """
        获取所有配置.

        Args:
            limit: 限制返回数量

        Returns:
            配置实例列表
        """
        with self.get_session() as session:
            query = select(SchedulerConfig)
            if limit:
                query = query.limit(limit)
            result = session.execute(query).scalars().all()
            return list(result)

    def update_crontab(
        self,
        collect_type: str,
        crontab_expression: str,
        is_active: bool
    ) -> SchedulerConfig | None:
        """
        更新定时任务配置.

        Args:
            collect_type: 采集类型
            crontab_expression: crontab表达式
            is_active: 是否激活

        Returns:
            配置实例或None
        """

        config = self.get_by_type(collect_type)
        if config:
            return self.update(
                config.id,
                crontab_expression=crontab_expression,
                is_active=is_active,
                updated_at=datetime.now()
            )
        else:
            # 创建新配置
            return self.create(
                collect_type=collect_type,
                crontab_expression=crontab_expression,
                is_active=is_active
            )

    def update_last_run_time(
        self,
        collect_type: str,
        run_time
    ) -> SchedulerConfig | None:
        """
        更新最后运行时间.

        Args:
            collect_type: 采集类型
            run_time: 运行时间

        Returns:
            配置实例或None
        """
        config = self.get_by_type(collect_type)
        if config:
            return self.update(
                config.id,
                last_run_time=run_time
            )
        return None
