"""定时任务调度模块."""
import logging

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from collector import PixivCollector
from database import db
from models import SchedulerConfig, SystemConfig
from rate_limiter import RateLimiter
from updater import ArtworkUpdater

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    定时任务调度器
    全局唯一，请不要额外new实例，import task_scheduler即可
    """

    def __init__(self, app=None):
        """
        初始化调度器.

        Args:
            app: Flask应用实例
        """
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.rate_limiter = None
        self.collector = None
        self.updater = None

        # 添加错误监听器
        self.scheduler.add_listener(
            self._job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
        )

    def _get_config_dict(self) -> dict:
        """从SystemConfig获取配置字典."""
        config_items = db.session.query(SystemConfig).all()
        config_dict = {}
        for item in config_items:
            config_dict[item.config_key] = item.to_dict()['value']
        return config_dict

    def _load_config(self) -> None:
        """从数据库加载配置并初始化速率限制器."""
        config_dict = self._get_config_dict()

        if not config_dict:
            logger.warning("No system config found, using defaults")
            config_dict = {}

        # 获取配置值，提供默认值
        delay_min = config_dict.get('api_delay_min', 1.0)
        delay_max = config_dict.get('api_delay_max', 3.0)
        error_delay_429_min = config_dict.get('error_delay_429_min', 30.0)
        error_delay_429_max = config_dict.get('error_delay_429_max', 60.0)
        error_delay_403_min = config_dict.get('error_delay_403_min', 30.0)
        error_delay_403_max = config_dict.get('error_delay_403_max', 50.0)
        error_delay_other_min = config_dict.get('error_delay_other_min', 10.0)
        error_delay_other_max = config_dict.get('error_delay_other_max', 30.0)

        # 初始化速率限制器
        self.rate_limiter = RateLimiter(
            delay_min=delay_min,
            delay_max=delay_max,
            error_delay_429_min=error_delay_429_min,
            error_delay_429_max=error_delay_429_max,
            error_delay_403_min=error_delay_403_min,
            error_delay_403_max=error_delay_403_max,
            error_delay_other_min=error_delay_other_min,
            error_delay_other_max=error_delay_other_max,
        )

        # 初始化采集器和更新器
        self.collector = PixivCollector(self.rate_limiter)
        self.updater = ArtworkUpdater(self.rate_limiter)

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
            from datetime import datetime
            config = db.session.query(SchedulerConfig).filter_by(
                collect_type=job_id
            ).first()
            if config:
                config.last_run_time = datetime.now()
                db.session.commit()
                logger.info(f"Updated run time for job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to update run time for {job_id}: {e}")

    def heartbeat(self) -> None:
        """后台任务心跳"""
        with self.app.app_context():
            logger.info("Scheduler alive")

    def _collect_ranking(self) -> None:
        """采集排行榜任务."""
        with self.app.app_context():
            logger.info("Starting rank collection job")
            self._collect_daily_rank()
            self._collect_weekly_rank()
            self._collect_monthly_rank()
            # 更新任务执行时间
            self._update_job_run_time('ranking_works')

    def _collect_daily_rank(self) -> None:
        """采集每日排行任务."""
        logger.info("Starting daily rank collection job")
        try:
            if not self.collector:
                return
            if self.collector.rate_limiter:
                self.collector.rate_limiter.wait()
            result = self.collector.collect_daily_rank()
            logger.info(f"Daily rank collection completed: {result}")
        except Exception as e:
            logger.error(f"Daily rank collection failed: {e}")

    def _collect_weekly_rank(self) -> None:
        """采集每周排行任务."""
        logger.info("Starting weekly rank collection job")
        try:
            if not self.collector:
                return
            if self.collector.rate_limiter:
                self.collector.rate_limiter.wait()
            result = self.collector.collect_weekly_rank()
            logger.info(f"Weekly rank collection completed: {result}")
        except Exception as e:
            logger.error(f"Weekly rank collection failed: {e}")

    def _collect_monthly_rank(self) -> None:
        """采集每月排行任务."""
        logger.info("Starting monthly rank collection job")
        try:
            if not self.collector:
                return
            if self.collector.rate_limiter:
                self.collector.rate_limiter.wait()
            result = self.collector.collect_monthly_rank()
            logger.info(f"Monthly rank collection completed: {result}")
        except Exception as e:
            logger.error(f"Monthly rank collection failed: {e}")

    def _sync_follows(self) -> None:
        """同步关注列表任务."""
        with self.app.app_context():
            logger.info("Starting follow sync job")
            try:
                if not self.collector:
                    return
                result = self.collector.sync_follows()
                logger.info(f"Follow sync completed: {result}")
                # 更新任务执行时间
                self._update_job_run_time('follow_new_follow')
            except Exception as e:
                logger.error(f"Follow sync failed: {e}")

    def _collect_follow_works(self) -> None:
        """采集关注用户新作品任务."""
        with self.app.app_context():
            logger.info("Starting follow works collection job")
            try:
                if not self.collector:
                    return
                result = self.collector.collect_follow_works()
                logger.info(f"Follow works collection completed: {result}")
                # 更新任务执行时间
                self._update_job_run_time('follow_new_works')
            except Exception as e:
                logger.error(f"Follow works collection failed: {e}")

    def _update_artworks(self) -> None:
        """更新作品元数据任务."""
        with self.app.app_context():
            logger.info("Starting artwork update job")
            try:
                if not self.updater:
                    return
                result = self.updater.update_artworks()
                logger.info(f"Artwork update completed: {result}")
                # 更新任务执行时间
                self._update_job_run_time('update_artworks')
            except Exception as e:
                logger.error(f"Artwork update failed: {e}")

    def _clean_up_logs(self) -> None:
        """清理旧日志任务."""
        with self.app.app_context():
            logger.info("Starting log cleanup job")
            try:
                # 执行清理
                if not self.collector:
                    return

                result = self.collector.clean_up_old_logs()
                logger.info(f"Log cleanup completed: {result}")

                # 更新任务执行时间
                self._update_job_run_time('cleanup_logs')

            except Exception as e:
                logger.error(f"Log cleanup failed: {e}")

    def _setup_jobs(self) -> None:
        """设置所有定时任务."""
        self._load_config()

        # 获取任务配置
        configs = db.session.query(SchedulerConfig).all()

        for config in configs:
            if not config.is_active:
                logger.info(f"Job {config.collect_type} is inactive, skipping")
                continue

            self._add_job(config)

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
            job_func = self._collect_follow_works
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
        configs = db.session.query(SchedulerConfig).all()
        jobs = self.scheduler.get_jobs()
        for config in configs:
            job_id = config.collect_type
            job = next((j for j in jobs if j.id == config.collect_type), None)
            if job:
                # Job 存在，更新 interval 并激活
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
