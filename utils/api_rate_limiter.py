"""API速率限制器（内存版，支持反向代理）."""
import functools
import logging
import time
from collections import defaultdict

from flask import jsonify, request

from config import Config
from services import services

logger = logging.getLogger(__name__)


def get_real_client_ip() -> str:
    """
    获取真实客户端IP（支持反向代理和CDN）.

    优先级：
    1. X-Forwarded-For (标准代理头)
    2. X-Real-IP (Nginx等)
    3. CF-Connecting-IP (Cloudflare)
    4. request.remote_addr (直连)

    Returns:
        客户端IP地址
    """
    # X-Forwarded-For格式: client, proxy1, proxy2
    # 取第一个IP（客户端真实IP）
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()

    # X-Real-IP
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()

    # Cloudflare
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip.strip()

    # 直连情况
    return request.remote_addr or 'unknown'


def get_identifier(api_endpoint: str | None = None) -> str:
    """
    获取标识符（优先使用API密钥，否则使用真实IP）.

    Args:
        api_endpoint: API端点名称

    Returns:
        标识符字符串
    """
    # 从Header获取API密钥
    api_key = request.headers.get('X-API-Key')

    if api_key:
        if api_endpoint:
            return f"{api_endpoint}:apikey:{api_key}"
        return f"apikey:{api_key}"

    # 使用真实IP
    ip = get_real_client_ip()
    if api_endpoint:
        return f"{api_endpoint}:ip:{ip}"
    return f"ip:{ip}"


class ApiRateLimiter:
    """基于内存的滑动窗口速率限制器."""

    def __init__(self):
        """
        初始化速率限制器.
        """

        self.rate_limit_no_key = Config.RATE_LIMIT_NO_KEY
        self.rate_limit_with_key = Config.RATE_LIMIT_WITH_KEY
        self.window_seconds = Config.RATE_LIMIT_WINDOW_SECONDS

        # 存储每个标识符的请求时间戳
        # 格式: {identifier: [timestamp1, timestamp2, ...]}
        self._request_records: defaultdict[str, list[float]] = (
            defaultdict(list)
        )

        # 最后清理时间
        self._last_cleanup_time: float = time.time()

    def _cleanup_expired_records(self) -> None:
        """清理过期的请求记录."""
        current_time = time.time()
        # 每60秒清理一次
        if current_time - self._last_cleanup_time < 60:
            return

        window_start = current_time - self.window_seconds

        for identifier in list(self._request_records.keys()):
            # 过滤掉过期的时间戳
            self._request_records[identifier] = [
                ts
                for ts in self._request_records[identifier]
                if ts > window_start
            ]

            # 如果列表为空，删除该键
            if not self._request_records[identifier]:
                del self._request_records[identifier]

        self._last_cleanup_time = current_time
        logger.debug(
            f"Cleaned up expired rate limit records, "
            f"active identifiers: {len(self._request_records)}"
        )

    def get_rate_limit(self, has_valid_key: bool) -> int:
        """
        获取速率限制次数.

        Args:
            has_valid_key: 是否有有效的API密钥

        Returns:
            限制次数
        """
        return (
            self.rate_limit_with_key
            if has_valid_key
            else self.rate_limit_no_key
        )

    def is_allowed(
        self, identifier: str, limit: int
    ) -> tuple[bool, int, int]:
        """
        检查是否允许请求.

        Args:
            identifier: 标识符
            limit: 限制次数

        Returns:
            (是否允许, 剩余次数, 重置时间)
        """
        # 清理过期记录
        self._cleanup_expired_records()

        current_time = time.time()
        window_start = current_time - self.window_seconds

        # 获取该标识符的请求记录
        records = self._request_records[identifier]

        # 过滤掉窗口外的记录
        records[:] = [
            ts for ts in records
            if ts > window_start
        ]

        # 检查是否超过限制
        count = len(records)
        if count < limit:
            # 允许请求，记录时间戳
            records.append(current_time)
            remaining = limit - count - 1
            reset_time = int(current_time + self.window_seconds)
            return True, remaining, reset_time
        else:
            # 超过限制
            remaining = 0
            # 获取最早请求的重置时间
            if records:
                reset_time = int(records[0] + self.window_seconds)
            else:
                reset_time = int(current_time + self.window_seconds)
            return False, remaining, reset_time


# 全局速率限制器实例
_rate_limiter: ApiRateLimiter | None = None


def get_rate_limiter() -> ApiRateLimiter:
    """
    获取速率限制器实例.

    Returns:
        ApiRateLimiter实例
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ApiRateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """重置速率限制器."""
    global _rate_limiter
    _rate_limiter = None


def rate_limit():
    """
    速率限制装饰器.

    Returns:
        装饰器函数
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # 获取速率限制器实例
            limiter = get_rate_limiter()

            # 使用函数名作为API端点，生成独立标识符
            api_endpoint = f.__name__
            identifier = get_identifier(api_endpoint)

            # 验证API密钥并更新统计
            api_key_str = request.headers.get('X-API-Key')
            has_valid_key = False

            if api_key_str:
                try:
                    api_key = services.api_key.get_by_key(api_key_str)
                    if api_key and api_key.is_active:
                        has_valid_key = True
                        # 更新使用统计
                        services.api_key.update_usage(api_key_str)
                except Exception as e:
                    logger.error(f"Failed to validate API key: {e}")

            # 获取限制次数
            limit = limiter.get_rate_limit(has_valid_key)

            # 检查速率限制
            allowed, remaining, reset_time = limiter.is_allowed(
                identifier, limit
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}, limit: {limit}"
                )
                response = jsonify({
                    'success': False,
                    'message': 'Rate limit exceeded',
                    'error': 'rate_limit_exceeded'
                })
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset_time)
                return response

            # 允许请求，执行原函数
            result = f(*args, **kwargs)

            # 如果返回的是Response对象，添加速率限制头
            if hasattr(result, 'headers'):
                result.headers['X-RateLimit-Limit'] = str(limit)
                result.headers['X-RateLimit-Remaining'] = str(remaining)
                result.headers['X-RateLimit-Reset'] = str(reset_time)

            return result

        return wrapper

    return decorator
