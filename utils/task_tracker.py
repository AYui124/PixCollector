"""Huey任务运行状态跟踪装饰器."""
import logging
import os
from datetime import datetime
from functools import wraps

from core.huey import huey

WORKER_ID = os.getpid()

logger = logging.getLogger('huey.tracker')


def track_task(fn):
    """
    任务状态跟踪装饰器.

    在任务执行前记录到redis，执行完成后删除。

    Args:
        fn: 被装饰的函数

    Returns:
        包装后的函数
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        key = f"huey:task:track:running:{fn.__name__}:{WORKER_ID}"
        # 记录任务开始信息
        _put_data(key, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        try:
            return fn(*args, **kwargs)
        finally:
            # 任务完成后清理记录
            _delete(key)

    return wrapper


_shutdown_called = False


@huey.on_shutdown()
def dump_running_tasks():
    """
    输出所有正在运行的任务.

    用于shutdown时查看未完成的任务。
    """
    global _shutdown_called
    if _shutdown_called:
        return
    _shutdown_called = True
    keys = search("huey:task:track:running:*")
    logger.info("Check running tasks...")
    count = 0
    for k in keys:
        data = _get_data(k)
        if data:
            start_time = (
                datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
                if data else None
            )
            duration = datetime.now() - start_time if start_time else None
            logger.info(f" + {k}")
            logger.info(f" + Start at {start_time}")
            logger.info(
                f" + Running for: "
                f"{(duration.total_seconds() if duration else 0):.2f}s"
            )
            count += 1
        else:
            logger.info(f" + {k} (no data)")
            count += 1
        _delete(k)

    if count == 0:
        logger.info("No running tasks")
    else:
        logger.info("Waiting for tasks finished...")


def _put_data(key: str, data: str):
    redis = huey.storage.conn
    redis.setex(
        key.encode(),
        3600,
        data.encode()
    )


def _get_data(key: str) -> str | None:
    k = key.encode()
    redis = huey.storage.conn
    pipe = redis.pipeline()
    pipe.exists(k)
    pipe.get(k)
    exists, val = pipe.execute()
    data = None if not exists else val.decode()
    return data


def _delete(key: str):
    redis = huey.storage.conn
    redis.delete(key.encode())


def search(key_partten: str) -> list[str]:
    redis = huey.storage.conn
    keys = redis.scan_iter(key_partten)
    return [x.decode('utf-8') for x in keys]
