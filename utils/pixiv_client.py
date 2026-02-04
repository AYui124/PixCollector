"""Pixiv API客户端（纯粹的API调用，不涉及数据库）."""
import logging
from datetime import datetime, timedelta
from typing import Any, Literal, cast

from pixivpy3 import ByPassSniApi
from pixivpy3.aapi import _MODE, _TYPE

logger = logging.getLogger(__name__)


class PixivClient:
    """Pixiv API客户端封装."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        user_id: int | None = None,
    ):
        """
        初始化Pixiv客户端.

        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌
            user_id: 用户ID（可选）
        """
        self._api = ByPassSniApi()
        self._api.set_auth(access_token, refresh_token)
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.token_expiry: datetime | None = None  # token过期时间

    def get_ranking(
        self,
        mode: str,
        offset: int = 0
    ) -> Any:
        """
        获取排行榜数据.

        Args:
            mode: 排行榜模式
            offset: 偏移量（分页使用）

        Returns:
            排行榜数据

        Raises:
            Exception: 获取失败
        """
        try:
            if mode not in ['day', 'week', 'month', '']:
                raise
            literal_mode = cast(_MODE, mode)
            return self._api.illust_ranking(mode=literal_mode, offset=offset)
        except Exception as e:
            logger.error(f"Failed to get ranking: {e}")
            raise

    def get_following(
        self,
        offset: int = 0
    ) -> Any:
        """
        获取关注列表.

        Args:
            user_id: 用户ID
            offset: 偏移量

        Returns:
            关注列表数据

        Raises:
            Exception: 获取失败
        """
        try:
            if not self.user_id:
                raise

            return self._api.user_following(int(self.user_id), offset=offset)
        except Exception as e:
            logger.error(f"Failed to get following: {e}")
            raise

    def get_user_illusts(
        self,
        user_id: int,
        offset: int | str = 0,
        illust_type: Literal['illust', 'manga', 'ugoira'] = 'illust'
    ) -> Any:
        """
        获取用户作品列表.

        Args:
            user_id: 用户ID
            offset: 偏移量
            illust_type: 作品类型

        Returns:
            作品列表数据

        Raises:
            Exception: 获取失败
        """
        try:
            literal_type = cast(_TYPE, illust_type)
            return self._api.user_illusts(
                user_id,
                offset=offset,
                type=literal_type
            )
        except Exception as e:
            logger.error(f"Failed to get user illusts: {e}")
            raise

    def get_follow_illusts(
        self,
        offset: int | str = 0,
        restrict: Literal['public', 'private'] = 'public'
    ) -> Any:
        """
        获取关注用户的作品.

        Args:
            offset: 偏移量
            restrict: 限制类型

        Returns:
            作品列表数据

        Raises:
            Exception: 获取失败
        """
        try:
            return self._api.illust_follow(
                restrict=restrict,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Failed to get follow illusts: {e}")
            raise

    def get_illust_detail(self, illust_id: int) -> Any:
        """
        获取作品详情.

        Args:
            illust_id: 作品ID

        Returns:
            作品详情数据

        Raises:
            Exception: 获取失败
        """
        try:
            return self._api.illust_detail(illust_id)
        except Exception as e:
            logger.error(f"Failed to get illust detail: {e}")
            raise

    def refresh_tokens(self) -> None:
        """
        刷新访问令牌.

        Returns:
            (新的access_token, 新的refresh_token)

        Raises:
            Exception: 刷新失败
        """
        try:
            # 使用refresh_token刷新
            self._api.auth(refresh_token=self.refresh_token)
            # 更新本地存储
            self.access_token = self._api.access_token or ''
            self.refresh_token = self._api.refresh_token or ''
            self.user_id = int(self._api.user_id) or 0
            # 设置过期时间为1小时后
            self.token_expiry = datetime.now() + timedelta(hours=1)

            logger.info("Tokens refreshed successfully")
            return
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {e}")
            raise

    def parse_qs(self, url: str) -> dict[str, Any] | None:
        """
        解析URL查询字符串.

        Args:
            url: URL

        Returns:
            查询参数字典
        """
        try:
            return self._api.parse_qs(url)
        except Exception as e:
            logger.error(f"Failed to parse query string: {e}")
            raise

    def verify_token(self) -> None:
        """
        验证token有效性，调用一次user_detail.

        Raises:
            Exception: token无效
        """
        try:
            # 调用get_user_id验证token
            user_id = self.user_id
            if not user_id:
                raise ValueError('Not login')
            user = self._api.user_detail(user_id)
            if user:
                logger.info(f"Token verified, user_id: {user_id}")
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            raise

    def search_illust(
        self,
        word: str,
        offset: int = 0,
    ) -> Any:
        """
        搜索插画作品.

        Args:
            word: 搜索关键词
            search_target: 搜索类型
                - partial_match_for_tags: 标签部分匹配
                - exact_match_for_tags: 标签完全匹配
                - title_and_caption: 标题和说明
                - keyword: 关键词
            sort: 排序方式
                - date_desc: 按发布时间降序（最新）
                - date_asc: 按发布时间升序
                - popular_desc: 热门排序（需会员）
            duration: 时间范围
                - within_last_day: 最近一天
                - within_last_week: 最近一周
                - within_last_month: 最近一月
            offset: 偏移量（分页）
            search_ai_type: AI作品类型
                - 0: 过滤AI作品
                - 1: 显示AI作品
                - None: 不限制

        Returns:
            搜索结果数据

        Raises:
            Exception: 搜索失败
        """
        try:
            return self._api.search_illust(
                word=word,
                search_target='partial_match_for_tags',
                sort='date_desc',
                offset=offset,
                search_ai_type=0,
            )
        except Exception as e:
            logger.error(f"Failed to search illust: {e}")
            raise
