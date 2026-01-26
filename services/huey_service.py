"""Huey异步任务服务."""
import logging
from datetime import datetime

from croniter import croniter
from huey import crontab

from config import Config
from core.huey import huey
from services import services

logger = logging.getLogger(__name__)


def init():
    logger.info('register task')


def _get_pixiv_service():
    """获取PixivService实例."""
    return services.pixiv


@huey.task()
def collect_daily_rank_task() -> dict:
    """
    异步采集每日排行榜.

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.collect_daily_rank()
        return result
    except Exception as e:
        logger.error(
            f"Daily rank collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def collect_weekly_rank_task() -> dict:
    """
    异步采集每周排行榜.

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.collect_weekly_rank()
        return result
    except Exception as e:
        logger.error(
            f"Weekly rank collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def collect_monthly_rank_task() -> dict:
    """
    异步采集每月排行榜.

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.collect_monthly_rank()
        return result
    except Exception as e:
        logger.error(
            f"Monthly rank collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def sync_follows_task() -> dict:
    """
    异步同步关注列表.

    Returns:
        同步结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.sync_follows()
        return result
    except Exception as e:
        logger.error(
            f"Follows sync task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def collect_user_artworks_task(
    user_id: int,
) -> dict:
    """
    异步采集单个用户的作品.

    Args:
        user_id: 用户ID
        backtrack_years: 回采年限

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    follow = services.follow.get_by_user_id(user_id)
    if not follow:
        return {
            'success': False,
            'message': f'User {user_id} not found in follows'
        }

    try:
        backtrack_years = pixiv_service.get_config_value(
            'new_user_backtrack_years', 2
        )
        result: dict = pixiv_service.collect_single_user_artworks(
            follow, backtrack_years
        )
        return result
    except Exception as e:
        logger.error(
            f"User artworks collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def collect_all_follow_artworks_task() -> dict:
    """
    异步采集所有关注用户的作品（初始全量）.

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.collect_all_follow_artworks()
        return result
    except Exception as e:
        logger.error(
            f"All follow artworks collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def collect_follow_new_works_task() -> dict:
    """
    异步采集关注用户新作品.

    Returns:
        采集结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.collect_follow_new_works()
        return result
    except Exception as e:
        logger.error(
            f"Follow new works collection task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task(expires=Config.HUEY_RESULT_TIMEOUT)
def update_artworks_task() -> dict:
    """
    异步更新作品元数据.

    Returns:
        更新结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.update_artworks()
        return result
    except Exception as e:
        logger.error(
            f"Artworks update task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


@huey.task()
def cleanup_logs_task() -> dict:
    """
    异步清理旧日志.

    Returns:
        清理结果
    """
    pixiv_service = _get_pixiv_service()
    if not pixiv_service:
        return {'success': False, 'message': 'Pixiv service not initialized'}

    try:
        result: dict = pixiv_service.clean_up_old_logs()
        return result
    except Exception as e:
        logger.error(
            f"Logs cleanup task failed: {e}",
            exc_info=True
        )
        return {'success': False, 'message': str(e)}


def get_task_status(task_id: str) -> dict:
    """
    获取任务状态.

    Args:
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    result = huey.result(task_id)

    # 获取任务元数据
    metadata = None
    try:
        task = huey.storage.get_task(task_id)
        if task:
            metadata = task.metadata
    except Exception:
        pass

    # 获取关联的采集日志
    recent_logs = services.collection.get_recent_logs(100)

    # 尝试找到与任务关联的日志
    log = None
    if metadata and 'log_type' in metadata:
        task_logs = [
            log_item for log_item in recent_logs
            if log_item.log_type == metadata['log_type'] and
            log_item.status in ('running', 'pending')
        ]
        if task_logs:
            log = task_logs[0]

    return {
        'task_id': task_id,
        'status': 'running' if result is None else 'completed',
        'result': result,
        'metadata': metadata,
        'log': log.to_dict() if log else None
    }


def _get_task_function(collect_type: str):
    """
    根据任务类型获取对应的任务函数.

    Args:
        collect_type: 任务类型

    Returns:
        任务函数或None
    """
    task_mapping = {
        'ranking_works': _execute_ranking_tasks,
        'follow_new_follow': sync_follows_task,
        'follow_new_works': collect_follow_new_works_task,
        'update_artworks': update_artworks_task,
        'clean_up_logs': cleanup_logs_task,
    }
    return task_mapping.get(collect_type)


def _execute_ranking_tasks():
    """执行所有排行榜采集任务."""
    tasks = [
        ('daily', collect_daily_rank_task),
        ('weekly', collect_weekly_rank_task),
        ('monthly', collect_monthly_rank_task)
    ]
    for rank_type, task_func in tasks:
        try:
            logger.info(f"Executing {rank_type} rank collection")
            task_func()
        except Exception as e:
            logger.error(
                f"{rank_type.capitalize()} rank collection failed: {e}",
                exc_info=True
            )


def _update_job_run_time(job_id: str) -> None:
    """
    更新任务最后执行时间.

    Args:
        job_id: 任务ID
    """
    try:
        services.scheduler.update_last_run_time(job_id, datetime.now())
        logger.info(f"Updated run time for job: {job_id}")
    except Exception as e:
        logger.error(f"Failed to update run time for {job_id}: {e}")


@huey.periodic_task(crontab())
def schedule_dispatcher_task():
    """
    动态定时任务分发器 - 每分钟执行一次.
    从数据库读取任务配置，根据cron表达式调度执行相应任务.
    """

    try:
        configs = services.scheduler.get_all_configs()

        if not configs:
            return

        current_time = datetime.now()

        for config in configs:
            if not config.is_active:
                continue

            # 获取任务函数
            task_func = _get_task_function(config.collect_type)
            if not task_func:
                logger.warning(f"Unknown job type: {config.collect_type}")
                continue

            # 使用croniter计算下次执行时间
            try:
                cron = croniter(config.crontab_expression, current_time)
                cron.get_next(datetime)

                # 如果上次执行时间为空，
                # 或者下次执行时间在当前时间之前（包括当前分钟）
                should_run = False
                if config.last_run_time is None:
                    should_run = True
                else:
                    # 计算基于上次执行时间的下一次应该执行的时间
                    cron_prev = croniter(
                        config.crontab_expression,
                        config.last_run_time
                    )
                    expected_next = cron_prev.get_next(datetime)
                    # 如果当前时间已经超过了预期执行时间，则应该执行
                    if current_time >= expected_next:
                        should_run = True

                if should_run:
                    logger.info(
                        f"Executing scheduled task: {config.collect_type}"
                    )
                    try:
                        # 调用任务函数
                        if config.collect_type == 'ranking_works':
                            # 排行榜任务执行后更新时间
                            _execute_ranking_tasks()
                        else:
                            # 其他任务异步执行
                            task_func()

                        # 更新最后执行时间
                        _update_job_run_time(config.collect_type)
                        logger.info(
                            f"Task {config.collect_type} executed successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"Task {config.collect_type} "
                            f"execution failed: {e}",
                            exc_info=True
                        )

            except Exception as e:
                logger.error(
                    f"Error parsing cron expression for "
                    f"{config.collect_type}: {e}",
                    exc_info=True
                )

    except Exception as e:
        logger.error(
            f"Scheduler dispatcher error: {e}",
            exc_info=True
        )
