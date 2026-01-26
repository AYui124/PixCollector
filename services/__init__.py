"""Service层初始化."""
from typing import TYPE_CHECKING

from services.artwork_service import ArtworkService
from services.auth_service import AuthService
from services.collection_service import CollectionService
from services.config_service import ConfigService
from services.follow_service import FollowService
from services.pixiv_service import PixivService
from services.scheduler_service import SchedulerService

if TYPE_CHECKING:
    from utils.pixiv_client import PixivClient
    from utils.rate_limiter import RateLimiter


class Tools:
    """工具容器类，提供类型安全的工具访问."""

    pixiv_client: 'PixivClient | None'
    rate_limiter: 'RateLimiter | None'

    def __init__(self) -> None:
        self.pixiv_client = None
        self.rate_limiter = None


class Services:
    """服务容器类，提供类型安全的服务访问."""

    _auth: 'AuthService | None' = None
    _collection: 'CollectionService | None' = None
    _config: 'ConfigService | None' = None
    _artwork: 'ArtworkService | None' = None
    _follow: 'FollowService | None' = None
    _scheduler: 'SchedulerService | None' = None
    _pixiv: 'PixivService | None' = None

    @property
    def auth(self) -> AuthService:
        """获取认证服务."""
        if self._auth is None:
            self._auth = AuthService.get_instance()
        return self._auth

    @auth.setter
    def auth(self, value):
        """设置认证服务."""
        self._auth = value

    @property
    def collection(self) -> CollectionService:
        """获取采集日志服务."""
        if self._collection is None:
            self._collection = CollectionService.get_instance()
        return self._collection

    @collection.setter
    def collection(self, value):
        """设置采集日志服务."""
        self._collection = value

    @property
    def config(self) -> ConfigService:
        """获取配置服务."""
        if self._config is None:
            self._config = ConfigService.get_instance()
        return self._config

    @config.setter
    def config(self, value):
        """设置配置服务."""
        self._config = value

    @property
    def artwork(self) -> ArtworkService:
        """获取作品服务."""
        if self._artwork is None:
            self._artwork = ArtworkService.get_instance()
        return self._artwork

    @artwork.setter
    def artwork(self, value):
        """设置作品服务."""
        self._artwork = value

    @property
    def follow(self) -> FollowService:
        """获取关注服务."""
        if self._follow is None:
            self._follow = FollowService.get_instance()
        return self._follow

    @follow.setter
    def follow(self, value):
        """设置关注服务."""
        self._follow = value

    @property
    def scheduler(self) -> SchedulerService:
        """获取定时任务服务."""
        if self._scheduler is None:
            self._scheduler = SchedulerService.get_instance()
        return self._scheduler

    @scheduler.setter
    def scheduler(self, value):
        """设置定时任务服务."""
        self._scheduler = value

    @property
    def pixiv(self) -> 'PixivService | None':
        """获取 Pixiv 服务（可能为 None）."""
        if self._pixiv is None:
            self._pixiv = PixivService.get_instance()
        return self._pixiv

    @pixiv.setter
    def pixiv(self, value):
        """设置 Pixiv 服务."""
        self._pixiv = value


# 全局实例
tools = Tools()
services = Services()


__all__ = [
    'PixivService',
    'ConfigService',
    'ArtworkService',
    'FollowService',
    'AuthService',
    'CollectionService',
    'SchedulerService',
    'Tools',
    'Services',
    'tools',
    'services'
]
