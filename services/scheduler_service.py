"""定时任务Service."""
from typing import ClassVar

from repositories.scheduler_repository import SchedulerRepository


class SchedulerService:
    """定时任务业务逻辑层."""

    _instance: ClassVar['SchedulerService | None'] = None

    def __init__(self, scheduler_repo: SchedulerRepository):
        """
        初始化Service.

        Args:
            scheduler_repo: 定时任务Repository
        """
        self._scheduler_repo = scheduler_repo

    @classmethod
    def get_instance(cls) -> 'SchedulerService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            SchedulerService实例
        """
        if cls._instance is None:
            scheduler_repo = SchedulerRepository.get_instance()
            cls._instance = cls(scheduler_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_all_configs(self) -> list:
        """
        获取所有定时任务配置.

        Returns:
            配置列表
        """
        return self._scheduler_repo.get_all()

    def update_configs(self, job_configs: dict) -> None:
        """
        批量更新定时任务配置.

        Args:
            job_configs: 任务配置字典
            {job_type: {crontab_expression, is_active}}
        """
        for job_type, job_config in job_configs.items():
            # 验证job_type
            valid_job_types = [
                'ranking_works',
                'follow_new_follow',
                'follow_new_works',
                'update_artworks',
                'clean_up_logs'
            ]

            if (
                job_type in valid_job_types and
                isinstance(job_config, dict)
            ):
                crontab = job_config.get('crontab_expression') or ''
                is_active = job_config.get('is_active', True)
                self._scheduler_repo.update_crontab(
                    job_type, crontab, is_active
                )
