"""时间处理工具模块."""
from datetime import UTC, datetime


def get_utc_now() -> datetime:
    """
    获取当前UTC时间.

    Returns:
        datetime: 当前UTC时间（不带时区信息）
    """
    return datetime.now(UTC).replace(tzinfo=None)


def to_local_time(utc_datetime: datetime | None) -> datetime | None:
    """
    将UTC时间转换为本地时间（不带时区信息）.

    Args:
        utc_datetime: UTC时间对象

    Returns:
        datetime: 本地时间对象（不带时区信息），如果输入为None则返回None
    """
    if utc_datetime is None:
        return None

    # 如果时间对象没有时区信息，假设它是UTC时间
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=UTC)

    # 转换为本地时间并移除时区信息
    local_datetime = utc_datetime.astimezone()
    return local_datetime.replace(tzinfo=None)


def format_datetime(
    dt: datetime | None,
    format_str: str = '%Y-%m-%d %H:%M:%S'
) -> str | None:
    """
    格式化时间为字符串.

    Args:
        dt: 时间对象（可以是UTC或本地时间）
        format_str: 格式化字符串，默认为 '%Y-%m-%d %H:%M:%S'

    Returns:
        str: 格式化后的时间字符串，如果输入为None则返回None
    """
    if dt is None:
        return None

    # 先转换为本地时间再格式化
    local_dt = to_local_time(dt)
    if local_dt is None:
        return None

    return local_dt.strftime(format_str)


def format_date(dt: datetime | None) -> str | None:
    """
    格式化日期部分为字符串（不包含时间）.

    Args:
        dt: 时间对象

    Returns:
        str: 格式化后的日期字符串，如果输入为None则返回None
    """
    return format_datetime(dt, '%Y-%m-%d')
