"""速率限制器."""
import logging
import random
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimiter:
    """Pixiv API 速率限制器."""

    def __init__(
        self,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
        error_delay_429_min: float = 30.0,
        error_delay_429_max: float = 60.0,
        error_delay_403_min: float = 30.0,
        error_delay_403_max: float = 50.0,
        error_delay_other_min: float = 10.0,
        error_delay_other_max: float = 30.0
    ):
        """
        初始化速率限制器.

        Args:
            delay_min: 正常请求最小延迟（秒）
            delay_max: 正常请求最大延迟（秒）
            error_delay_429_min: 429错误最小延迟（秒）
            error_delay_429_max: 429错误最大延迟（秒）
            error_delay_403_min: 403错误最小延迟（秒）
            error_delay_403_max: 403错误最大延迟（秒）
            error_delay_other_min: 其他错误最小延迟（秒）
            error_delay_other_max: 其他错误最大延迟（秒）
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.error_delay_429_min = error_delay_429_min
        self.error_delay_429_max = error_delay_429_max
        self.error_delay_403_min = error_delay_403_min
        self.error_delay_403_max = error_delay_403_max
        self.error_delay_other_min = error_delay_other_min
        self.error_delay_other_max = error_delay_other_max

        self.last_request_time: datetime | None = None
        self.last_error_time: datetime | None = None
        self.last_error_code: int | None = None

    def wait(self) -> None:
        """等待直到可以发送下一个请求."""
        # 如果有最近的错误，根据错误代码等待
        if self.last_error_time and self.last_error_code:
            delay = self._get_error_delay(self.last_error_code)
            elapsed = (datetime.now() - self.last_error_time).total_seconds()

            if elapsed < delay:
                wait_time = delay - elapsed
                logger.info(
                    f"Waiting {wait_time:.2f}s due to "
                    f"previous {self.last_error_code} error"
                )
                time.sleep(wait_time)

            self.last_error_time = None
            self.last_error_code = None
        else:
            # 正常延迟
            if self.last_request_time:
                elapsed = (
                    datetime.now() - self.last_request_time
                ).total_seconds()
                delay = random.uniform(self.delay_min, self.delay_max)

                if elapsed < delay:
                    wait_time = delay - elapsed
                    time.sleep(wait_time)

        self.last_request_time = datetime.now()

    def fast_wait(self, delay_min: float, delay_max: float) -> None:
        delay = random.uniform(delay_min, delay_max)
        time.sleep(delay)

    def handle_error(
        self, error_code: int | None = None
    ) -> None:
        """
        处理错误，设置错误延迟。

        Args:
            error_code: HTTP错误代码
        """
        self.last_error_time = datetime.now()
        self.last_error_code = error_code

    def _get_error_delay(self, error_code: int | None) -> float:
        """
        获取错误延迟时间.

        Args:
            error_code: HTTP错误代码

        Returns:
            延迟时间（秒）
        """
        if error_code == 429:
            return random.uniform(
                self.error_delay_429_min,
                self.error_delay_429_max
            )
        elif error_code == 403:
            return random.uniform(
                self.error_delay_403_min,
                self.error_delay_403_max
            )
        else:
            return random.uniform(
                self.error_delay_other_min,
                self.error_delay_other_max
            )

    def batch_wait(
        self, count: int, interval: int = 5
    ) -> bool:
        """
        批量等待，每interval次请求后暂停一次.

        Args:
            count: 当前请求数
            interval: 间隔次数

        Returns:
            是否暂停
        """
        if count > 0 and count % interval == 0:
            delay = random.uniform(self.delay_min, self.delay_max)
            logger.info(f"Batch wait: {delay:.2f}s")
            time.sleep(delay)
            return True
        return False
