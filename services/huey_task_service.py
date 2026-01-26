"""Huey异步任务服务."""
import logging

from config import Config
from core.huey import huey
from repositories.collection_repository import CollectionRepository
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
    log_repo = CollectionRepository()
    recent_logs = log_repo.get_recent(100)

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
