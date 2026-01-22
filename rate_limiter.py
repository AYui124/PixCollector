"""速率限制器，用于防风控."""
import logging
import random
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """带有随机延时的速率限制器，避免反爬虫措施."""

    def __init__(
        self,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
        error_delay_429_min: float = 30.0,
        error_delay_429_max: float = 60.0,
        error_delay_403_min: float = 60.0,
        error_delay_403_max: float = 120.0,
        error_delay_other_min: float = 10.0,
        error_delay_other_max: float = 20.0,
    ):
        """
        初始化速率限制器.

        Args:
            delay_min: API调用最小延时
            delay_max: API调用最大延时
            error_delay_429_min: 429错误最小延时
            error_delay_429_max: 429错误最大延时
            error_delay_403_min: 403错误最小延时
            error_delay_403_max: 403错误最大延时
            error_delay_other_min: 其他错误最小延时
            error_delay_other_max: 其他错误最大延时
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.error_delay_429_min = error_delay_429_min
        self.error_delay_429_max = error_delay_429_max
        self.error_delay_403_min = error_delay_403_min
        self.error_delay_403_max = error_delay_403_max
        self.error_delay_other_min = error_delay_other_min
        self.error_delay_other_max = error_delay_other_max

    def wait(
        self,
        randomMin: float | None = None,
        randomMax: float | None = None
    ) -> None:
        """
        等待随机时长.

        Args:
            duration: 特定等待时长，如果为None则使用随机延时
        """
        if (
            randomMin and randomMax
            and randomMin < randomMax
            and randomMin > 0
        ):
            delay = random.uniform(randomMin, randomMax)
        else:
            delay = random.uniform(self.delay_min, self.delay_max)

        logger.debug(f"Rate limiter: waiting {delay:.2f} seconds")
        time.sleep(delay)

    def handle_error(self, status_code: int | None = None) -> None:
        """
        处理错误并等待适当时长.

        Args:
            status_code: HTTP状态码
        """
        if status_code == 429:
            delay = random.uniform(
                self.error_delay_429_min,
                self.error_delay_429_max
            )
            logger.warning(
                f"Rate limited (429), "
                f"waiting {delay:.2f} seconds"
            )
        elif status_code == 403:
            delay = random.uniform(
                self.error_delay_403_min,
                self.error_delay_403_max
            )
            logger.warning(
                f"Access forbidden (403), "
                f"waiting {delay:.2f} seconds"
            )
        else:
            delay = random.uniform(
                self.error_delay_other_min,
                self.error_delay_other_max
            )
            logger.warning(
                f"Error occurred, "
                f"waiting {delay:.2f} seconds"
            )

        time.sleep(delay)

    def batch_wait(self, count: int, interval: int = 20) -> bool:
        """
        处理批量项目后等待.

        Args:
            count: 当前批次数
            interval: 批次间隔大小

        Returns:
            bool: 是否触发了等待
        """
        if count > 0 and count % interval == 0:
            delay = random.uniform(5.0, 15.0)
            logger.info(
                f"Processed {count} items, "
                f"taking a break for {delay:.2f} seconds"
            )
            time.sleep(delay)
            return True
        return False
