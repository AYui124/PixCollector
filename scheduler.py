"""定时任务调度模块（不依赖Flask）."""
import logging
from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from models.scheduler_config import SchedulerConfig
from repositories.collection_repository import CollectionRepository
from repositories.config_repository import ConfigRepository
from repositories.scheduler_repository import SchedulerRepository
from services.config_service import ConfigService
from services.pixiv_service import PixivService

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    定时任务调度器（不依赖Flask）.
    全局唯一，请不要额外new实例，import task_scheduler即可
    """

    def __init__(self):
        """初始化调度器."""
        self.scheduler = BackgroundScheduler()
        self.pixiv_service = None

        # Repositories
        self._config_repo = ConfigRepository()
        self._scheduler_repo = SchedulerRepository()
        self._collection_repo = CollectionRepository()

        # Services
        self._config_service = ConfigService(self._config_repo)

        # 添加错误监听器
        self.scheduler.add_listener(
            self._job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
        )

    def _load_config(self) -> None:
        """从数据库加载配置并初始化组件."""
        config_dict = self._config_service.get_all_config()
        refresh_token = config_dict.get('refresh_token', '')

        if not refresh_token:
            logger.warning("No refresh_token found in config")
            return

        # 初始化Pixiv服务（client和limiter由service内部初始化）
        from repositories.artwork_repository import ArtworkRepository
        from repositories.follow_repository import FollowRepository

        self.pixiv_service = PixivService(
            artwork_repo=ArtworkRepository(),
            follow_repo=FollowRepository(),
            collection_repo=self._collection_repo,
            config_service=self._config_service
            # 无需传入client和limiter，service会自动初始化
        )

        logger.info("Configuration loaded and components initialized")

    def _job_listener(self, event) -> None:
        """
        任务事件监听器.

        Args:
            event: 调度器事件
        """
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} completed successfully")

    def _update_job_run_time(self, job_id: str) -> None:
        """
        更新任务最后执行时间.

        Args:
            job_id: 任务ID
        """
        try:
            self._scheduler_repo.update_last_run_time(job_id, datetime.now())
            logger.info(f"Updated run time for job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to update run time for {job_id}: {e}")

    def heartbeat(self) -> None:
        """后台任务心跳."""
        logger.info("Scheduler alive")

    def _collect_ranking(self) -> None:
        """采集排行榜任务."""
        logger.info("Starting rank collection job")
        try:
            if not self.pixiv_service:
                return
            self.pixiv_service.collect_daily_rank()
            self.pixiv_service.collect_weekly_rank()
            self.pixiv_service.collect_monthly_rank()
            self._update_job_run_time('ranking_works')
        except Exception as e:
            logger.error(f"Rank collection failed: {e}")

    def _sync_follows(self) -> None:
        """同步关注列表任务."""
        logger.info("Starting follow sync job")
        try:
            if not self.pixiv_service:
                return
            self.pixiv_service.sync_follows()
            self._update_job_run_time('follow_new_follow')
        except Exception as e:
            logger.error(f"Follow sync failed: {e}")

    def _collect_follow_new_works(self) -> None:
        """采集关注用户新作品任务."""
        logger.info("Starting follow new works collection job")
        try:
            if not self.pixiv_service:
                return
            self.pixiv_service.collect_follow_new_works()
            self._update_job_run_time('follow_new_works')
        except Exception as e:
            logger.error(f"Follow new works collection failed: {e}")

    def _update_artworks(self) -> None:
        """更新作品元数据任务."""
        logger.info("Starting artwork update job")
        try:
            if not self.pixiv_service:
                return
            self.pixiv_service.update_artworks()
            self._update_job_run_time('update_artworks')
        except Exception as e:
            logger.error(f"Artwork update failed: {e}")

    def _clean_up_logs(self) -> None:
        """清理旧日志任务."""
        logger.info("Starting log cleanup job")
        try:
            # 获取保留天数配置（已自动转换）
            config = self._config_service.get_all_config()
            retention_days = config.get('log_retention_days', 30)
            deleted_count = self._collection_repo.delete_old_logs(
                retention_days
            )
            logger.info(f"Deleted {deleted_count} old logs")
            self._update_job_run_time('clean_up_logs')
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")

    def _setup_jobs(self) -> None:
        """设置所有定时任务."""
        self._load_config()

        # 获取任务配置
        configs = self._scheduler_repo.get_all()

        for config in configs:
            if not config.is_active:
                logger.info(f"Job {config.collect_type} is inactive, skipping")
                continue

            self._add_job(config)

        # 添加心跳任务
        self.scheduler.add_job(
            self.heartbeat,
            'interval',
            seconds=60 * 10,
            id='heartbeat'
        )
        logger.info("All jobs configured")

    def _add_job(self, config: SchedulerConfig) -> None:
        """
        添加单个任务.

        Args:
            config: 任务配置
        """
        job_id = config.collect_type
        crontab_expr = config.crontab_expression

        # 根据类型选择任务函数
        job_func = None
        if config.collect_type == 'ranking_works':
            job_func = self._collect_ranking
        elif config.collect_type == 'follow_new_follow':
            job_func = self._sync_follows
        elif config.collect_type == 'follow_new_works':
            job_func = self._collect_follow_new_works
        elif config.collect_type == 'update_artworks':
            job_func = self._update_artworks
        elif config.collect_type == 'clean_up_logs':
            job_func = self._clean_up_logs
        else:
            logger.warning(f"Unknown job type: {config.collect_type}")
            return

        # 使用CronTrigger
        trigger = CronTrigger.from_crontab(crontab_expr)
        # 添加任务，CronTrigger会自动计算next_run_time
        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=job_id.replace('_', ' ').title(),
            max_instances=1,
            coalesce=True,
            misfire_grace_time=24 * 3600  # 24小时（1天）
        )

        logger.info(
            f"Job {job_id} added with cron expression: {crontab_expr}"
        )

    def _update_job(self, config: SchedulerConfig) -> None:
        """
        动态更新现有任务.
        """
        job_id = config.collect_type

        if not config.is_active:
            # 如果任务被禁用，移除它
            self.scheduler.remove_job(job_id)
            logger.info(f"Disabled job: {job_id}")
            return

        # 使用CronTrigger
        trigger = CronTrigger.from_crontab(config.crontab_expression)

        self.scheduler.reschedule_job(
            job_id,
            trigger=trigger
        )
        logger.info(
            f"Updated job: {job_id} "
            f"with cron expression: {config.crontab_expression}"
        )

    def start(self) -> None:
        """启动调度器."""
        self._setup_jobs()
        self.scheduler.start()
        logger.info("Task scheduler started")

    def shutdown(self) -> None:
        """关闭调度器."""
        self.scheduler.shutdown()
        logger.info("Task scheduler shutdown")

    def refresh_jobs(self) -> None:
        """动态刷新所有任务配置（无需重启）."""
        configs = self._scheduler_repo.get_all()
        jobs = self.scheduler.get_jobs()

        for config in configs:
            job_id = config.collect_type
            job = next((j for j in jobs if j.id == config.collect_type), None)
            if job:
                self._update_job(config)
            else:
                if config.is_active:
                    self._add_job(config)

        # 移除数据库中不存在的任务
        existing_job_ids = {job.id for job in self.scheduler.get_jobs()}
        for job_id in existing_job_ids:
            if job_id == 'heartbeat':
                continue
            if not any(config.collect_type == job_id for config in configs):
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed job: {job_id}")

        logger.info("Jobs refreshed dynamically")


# 全局调度器实例
task_scheduler = TaskScheduler()
