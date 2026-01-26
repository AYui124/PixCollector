"""Pixiv采集和更新服务."""
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select

from models.follow import Follow
from repositories.artwork_repository import ArtworkRepository
from repositories.collection_repository import CollectionRepository
from repositories.follow_repository import FollowRepository
from services.config_service import ConfigService
from utils.pixiv_client import PixivClient
from utils.rate_limiter import RateLimiter
from utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


class PixivService:
    """Pixiv业务服务（整合采集和更新功能）."""

    _instance: ClassVar['PixivService | None'] = None

    def __init__(
        self,
        artwork_repo: ArtworkRepository,
        follow_repo: FollowRepository,
        collection_repo: CollectionRepository,
        config_service: ConfigService,
        pixiv_client: PixivClient | None = None,
        rate_limiter: RateLimiter | None = None
    ):
        """
        初始化Pixiv服务.

        Args:
            artwork_repo: 作品Repository
            follow_repo: 关注Repository
            collection_repo: 采集日志Repository
            config_service: 配置Service
            pixiv_client: Pixiv客户端（可选，未提供则自动初始化）
            rate_limiter: 速率限制器（可选，未提供则自动初始化）
        """
        self._artwork_repo = artwork_repo
        self._follow_repo = follow_repo
        self._collection_repo = collection_repo
        self._config_service = config_service

        # 可选的外部依赖，未提供则内部初始化
        self._client = pixiv_client
        self._limiter = rate_limiter

    @classmethod
    def get_instance(cls) -> 'PixivService | None':
        """
        获取单例实例，如果配置不完整则返回 None.

        Returns:
            PixivService实例或None
        """
        # 先获取 ConfigService
        config_service = ConfigService.get_instance()

        # 检查是否有 refresh_token
        config_dict = config_service.get_all_config()
        if not config_dict.get('refresh_token'):
            return None

        # 如果已有实例直接返回
        if cls._instance is not None:
            return cls._instance

        # 获取依赖的 repositories
        artwork_repo = ArtworkRepository.get_instance()
        follow_repo = FollowRepository.get_instance()
        collection_repo = CollectionRepository.get_instance()

        # 创建实例（不传入 client 和 limiter，由内部懒加载）
        cls._instance = cls(
            artwork_repo=artwork_repo,
            follow_repo=follow_repo,
            collection_repo=collection_repo,
            config_service=config_service
        )
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def _ensure_initialized(self) -> None:
        """确保client和limiter已初始化."""
        if self._client is None or self._limiter is None:
            self._init_client_and_limiter()

    def _init_client_and_limiter(self) -> None:
        """内部初始化client和limiter."""
        # 获取配置
        config_dict = self._config_service.get_all_config()
        access_token = str(config_dict.get('access_token') or '')
        refresh_token = str(config_dict.get('refresh_token') or '')
        if not refresh_token:
            raise ValueError("No refresh_token found in config")

        # 获取user_id
        user_id = self._config_service.get_user_id()

        # 初始化RateLimiter
        delay_min = float(config_dict.get('api_delay_min') or 1.0)
        delay_max = float(config_dict.get('api_delay_max') or 3.0)
        error_delay_429_min = float(
            config_dict.get('error_delay_429_min') or 30.0
        )
        error_delay_429_max = float(
            config_dict.get('error_delay_429_max') or 60.0
        )
        error_delay_403_min = float(
            config_dict.get('error_delay_403_min') or 30.0
        )
        error_delay_403_max = float(
            config_dict.get('error_delay_403_max') or 50.0
        )
        error_delay_other_min = float(
            config_dict.get('error_delay_other_min') or 10.0
        )
        error_delay_other_max = float(
            config_dict.get('error_delay_other_max') or 30.0
        )

        self._limiter = RateLimiter(
            delay_min=delay_min,
            delay_max=delay_max,
            error_delay_429_min=error_delay_429_min,
            error_delay_429_max=error_delay_429_max,
            error_delay_403_min=error_delay_403_min,
            error_delay_403_max=error_delay_403_max,
            error_delay_other_min=error_delay_other_min,
            error_delay_other_max=error_delay_other_max,
        )

        # 初始化PixivClient，传入user_id
        self._client = PixivClient(access_token, refresh_token, user_id)

        # 从数据库加载token_expiry
        token_expiry_str = str(config_dict.get('token_expires_at') or '')
        if token_expiry_str:
            try:
                self._client.token_expiry = datetime.strptime(
                    token_expiry_str, '%Y-%m-%d %H:%M:%S'
                )
                logger.info(
                    f"Token expiry loaded: {self._client.token_expiry}"
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse token_expiry: {e}"
                )
                self._client.token_expiry = None
        else:
            self._client.token_expiry = None

    @property
    def client(self) -> PixivClient:
        """获取PixivClient，懒加载初始化."""
        if self._client is None:
            self._init_client_and_limiter()
        if self._client is None:
            raise ValueError("PixivClient initialize failed")
        return self._client

    @property
    def limiter(self) -> RateLimiter:
        """获取RateLimiter，懒加载初始化."""
        if self._limiter is None:
            self._init_client_and_limiter()
        if self._limiter is None:
            raise ValueError("RateLimiter initialize failed")
        return self._limiter

    def reload_components(self) -> None:
        """重新加载client和limiter（配置更新后调用）."""
        self._client = None
        self._limiter = None
        logger.info("Pixiv components will be reloaded on next access")

    def _parse_create_date(self, create_date: str) -> datetime:
        """
        解析作品创建日期（UTC）.

        Args:
            create_date: Pixiv API 返回的日期字符串

        Returns:
            UTC 日期时间
        """
        post_date_with_tz = datetime.strptime(
            create_date,
            '%Y-%m-%dT%H:%M:%S%z'
        )
        return post_date_with_tz.astimezone(UTC).replace(tzinfo=None)

    def _parse_create_date_with_local(
        self, create_date: str
    ) -> tuple[datetime, date | None]:
        """
        解析作品创建日期（UTC + 本地日期）.

        Args:
            create_date: Pixiv API 返回的日期字符串

        Returns:
            (UTC 日期时间, 本地日期)
        """
        post_date_with_tz = datetime.strptime(
            create_date,
            '%Y-%m-%dT%H:%M:%S%z'
        )
        post_date = post_date_with_tz.astimezone(UTC).replace(tzinfo=None)
        rank_date = post_date_with_tz.astimezone().date()
        return post_date, rank_date

    def _parse_offset(self, next_url: str | None) -> int:
        """
        从 next_url 解析 offset.

        Args:
            next_url: 下一页URL

        Returns:
            offset 值
        """
        if not next_url:
            return 0

        qs = self.client.parse_qs(next_url)
        offset = int(qs.get('offset') or 0) if qs else 0
        return offset

    def get_config_value(self, key: str, default=None):
        """
        获取配置值.

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        config_dict = self._config_service.get_all_config()
        return config_dict.get(key, default)

    def _ensure_valid_token(self) -> None:
        """确保token有效，过期则自动刷新并保存到数据库."""
        # 1. 检查本地有效期（数据库）
        expiry = self._config_service.get_token_expiry()
        now = get_utc_now()

        # 2. 如果有效期有效，直接返回
        if expiry and expiry > now:
            if not self.client.user_id:
                logger.debug(
                    f"Token is valid until {expiry}, "
                    f"but user_id is empty, refresh"
                )
            else:
                logger.debug(f"Token is valid until {expiry}")
                return

        # 3. 过期则刷新
        logger.warning(
            f"Token expired at UTC:{expiry or 'N/A'}, "
            f"refreshing..."
        )
        self.client.refresh_tokens()
        # 4. 保存新token（access_token + refresh_token + user_id + expiry）
        new_expiry = now + timedelta(hours=1)
        self._config_service.save_tokens(
            self.client.access_token,
            self.client.refresh_token,
            self.client.user_id
        )
        self._config_service.set_token_expiry(new_expiry)

        # 8. 验证token（调用一次user_detail）
        try:
            self.client.verify_token()
            logger.info(f"Token verified, valid until UTC:{new_expiry}")
        except Exception as e:
            logger.warning(f"Token verification failed after refresh: {e}")

    def collect_rank(self, mode: str) -> dict:
        """
        采集排行榜.

        Args:
            mode: 排行榜模式 (day/week/month)

        Returns:
            采集结果
        """
        self._ensure_initialized()

        log_type = 'ranking_works'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message=f'Starting {log_type} collection'
        )

        try:
            # 确保token有效
            self._ensure_valid_token()

            artworks_list = []

            # 获取排行榜数据
            logger.info(f"Fetching {mode} ranking...")
            rank_data = self.client.get_ranking(mode)
            self.limiter.wait()

            # 验证返回数据
            if (
                not rank_data
                or not hasattr(rank_data, 'illusts')
                or not rank_data.illusts
            ):
                raise ValueError(f"No illusts found in {mode} ranking data")

            logger.info(
                f"{mode.capitalize()} ranking result count: "
                f"{len(rank_data.illusts)}"
            )

            # 处理每个作品
            for item in rank_data.illusts:
                try:
                    artwork_pages = self._parse_artwork(item)
                    for artwork_data in artwork_pages:
                        artwork_data['collect_type'] = log_type
                        artworks_list.append(artwork_data)
                except Exception as e:
                    logger.error(f"Failed to parse artwork {item.id}: {e}")
                    continue

            # 批量保存
            saved_count = self._artwork_repo.batch_create(artworks_list)

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                f'Collected {saved_count} artworks from {log_type}',
                saved_count
            )

            return {'success': True, 'count': saved_count}

        except Exception as e:
            logger.error(f"Failed to collect {log_type}: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def collect_daily_rank(self) -> dict:
        """采集每日排行榜."""
        return self.collect_rank('day')

    def collect_weekly_rank(self) -> dict:
        """采集每周排行榜."""
        return self.collect_rank('week')

    def collect_monthly_rank(self) -> dict:
        """采集每月排行榜."""
        return self.collect_rank('month')

    def sync_follows(self) -> dict:
        """同步关注列表."""
        self._ensure_initialized()

        log_type = 'follow_new_follow'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message='Starting follow sync'
        )

        try:
            # 确保token有效
            self._ensure_valid_token()

            new_follows = 0
            has_more = True
            offset = 0
            query_count = 1

            user_id = self.client.user_id
            if not user_id:
                self._collection_repo.update_error(
                    log.id,
                    f'Synced {new_follows} failed, no current pixiv user id'
                )
                return {'success': False, 'new_follows': new_follows}

            while has_more:
                try:
                    # 获取关注列表
                    follows_data = self.client.get_following(offset)
                    self.limiter.wait()

                    # 验证返回数据
                    if not follows_data or not hasattr(
                        follows_data, 'user_previews'
                    ):
                        logger.warning("No user previews found in follow data")
                        break

                    if not follows_data.user_previews:
                        logger.warning("User previews is empty")
                        has_more = False
                        break

                    logger.info(
                        f"User previews count: "
                        f"{len(follows_data.user_previews)}"
                    )

                    # 处理每个用户
                    for user_info in follows_data.user_previews:
                        user_info_id = int(user_info.user.id)
                        existing = self._follow_repo.get_by_user_id(
                            user_info_id
                        )

                        if not existing:
                            # 新关注用户
                            self._follow_repo.create(
                                id=None,
                                user_id=user_info_id,
                                user_name=user_info.user.name,
                                avatar_url=(
                                    user_info.user.profile_image_urls.medium
                                    if user_info.user.profile_image_urls
                                    else None
                                ),
                                first_collect_date=get_utc_now(),
                                created_at=get_utc_now(),
                                updated_at=get_utc_now()
                            )
                            new_follows += 1
                            logger.info(
                                f"New follow: {user_info.user.name}"
                            )
                        else:
                            # 已存在，停止同步
                            logger.info(
                                f"已存在用户 {user_info.user.name}，"
                                f"停止同步"
                            )
                            has_more = False
                            break

                    query_count += 1

                    # 检查是否还有更多
                    if not follows_data.next_url:
                        has_more = False
                    else:
                        offset = self._parse_offset(follows_data.next_url)
                        logger.debug(
                            'next_url=%s,offset=%s',
                            follows_data.next_url,
                            offset
                        )

                    # 批量等待
                    if self.limiter.batch_wait(query_count, 5):
                        logger.info("Pause in sync_follows")

                except Exception as e:
                    logger.error(f"Error processing page {query_count}: {e}")
                    self.limiter.handle_error()
                    break

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                f'Synced {new_follows} new follows'
            )

            return {'success': True, 'new_follows': new_follows}

        except Exception as e:
            logger.error(f"Failed to sync follows: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def _parse_artwork(self, item) -> list[dict]:
        """
        解析作品数据.

        Args:
            item: Pixiv API返回的作品项

        Returns:
            解析后的作品数据列表
        """
        # 解析标签
        tags = []
        if hasattr(item, 'tags'):
            tags = [tag.name for tag in item.tags]

        # 判断R18
        is_r18 = self._classify_content(item, tags)

        # 解析rank
        rank = None
        if hasattr(item, 'rank') and item.rank:
            rank = int(str(item.rank).split('#')[0])

        # 解析日期
        post_date = None
        rank_date = None
        if hasattr(item, 'create_date'):
            post_date, rank_date = self._parse_create_date_with_local(
                item.create_date
            )

        # 解析作品类型
        artwork_type = 'illust'
        if hasattr(item, 'type'):
            artwork_type = item.type
        elif hasattr(item, 'illust_type'):
            artwork_type = item.illust_type

        # 获取页数
        page_count = item.page_count if hasattr(item, 'page_count') else 1

        # 生成分享URL
        share_url = f"https://www.pixiv.net/artworks/{item.id}"

        # 处理多图作品
        artworks_list = []
        is_valid = artwork_type == 'illust' and '漫画' not in tags
        err_msg = (
            artwork_type if artwork_type != 'illust' else 'Not like'
        )

        if hasattr(item, 'meta_pages') and item.meta_pages:
            # 多图作品
            for page_index in range(page_count):
                if page_index < len(item.meta_pages):
                    page_url = item.meta_pages[page_index].image_urls.large
                else:
                    page_url = (
                        item.image_urls.large
                        if item.image_urls else ''
                    )

                artworks_list.append({
                    'id': None,
                    'illust_id': item.id,
                    'title': item.title,
                    'author_id': item.user.id,
                    'author_name': item.user.name,
                    'url': page_url,
                    'share_url': share_url,
                    'page_index': page_index,
                    'page_count': page_count,
                    'total_bookmarks': (
                        item.total_bookmarks
                        if hasattr(item, 'total_bookmarks') else 0
                    ),
                    'total_view': (
                        item.total_view
                        if hasattr(item, 'total_view') else 0
                    ),
                    'rank': rank,
                    'rank_date': (
                        datetime.combine(rank_date, datetime.min.time())
                        if rank_date else None
                    ),
                    'post_date': post_date,
                    'tags': ','.join(tags),
                    'is_r18': bool(is_r18),
                    'type': artwork_type,
                    'is_valid': bool(is_valid),
                    'error_message': err_msg,
                    'last_updated_at': post_date,
                    'collect_type': '',
                    'created_at': get_utc_now()
                })
        else:
            # 单图作品
            artworks_list.append({
                'id': None,
                'illust_id': item.id,
                'title': item.title,
                'author_id': item.user.id,
                'author_name': item.user.name,
                'url': item.image_urls.large if item.image_urls else '',
                'share_url': share_url,
                'page_index': 0,
                'page_count': page_count,
                'total_bookmarks': (
                    item.total_bookmarks
                    if hasattr(item, 'total_bookmarks') else 0
                ),
                'total_view': (
                    item.total_view
                    if hasattr(item, 'total_view') else 0
                ),
                'rank': rank,
                'rank_date': (
                    datetime.combine(rank_date, datetime.min.time())
                    if rank_date
                    else None
                ),
                'post_date': post_date,
                'tags': ','.join(tags),
                'is_r18': bool(is_r18),
                'type': artwork_type,
                'is_valid': bool(is_valid),
                'error_message': err_msg,
                'last_updated_at': post_date,
                'collect_type': '',
                'created_at': get_utc_now()
            })

        return artworks_list

    def collect_single_user_artworks(
        self, follow: Follow, backtrack_years: int = 2
    ) -> dict:
        """
        采集单个用户的作品.

        Args:
            follow: 关注实例
            backtrack_years: 回采年限
            force_update: 是否强制更新

        Returns:
            采集结果
        """
        self._ensure_initialized()

        log_type = 'follow_user_artworks'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message=f'Starting collection for user {follow.user_name}'
        )

        try:
            # 确保token有效
            self._ensure_valid_token()

            artworks_list = []
            collected_count = 0
            last_artwork_date = None

            # 计算预设的回采截止日期
            initial_cutoff_date = (
                get_utc_now() - timedelta(days=backtrack_years * 365)
            )
            # 使用预设截止日期作为初始值
            actual_cutoff_date = initial_cutoff_date
            first_artwork_date = None

            has_more = True
            offset = 0
            page = 1

            while has_more:
                try:
                    logger.info(f'collect {follow.user_name} page:{page}')
                    # 获取用户作品
                    user_illusts = self.client.get_user_illusts(
                        follow.user_id, offset
                    )
                    self.limiter.wait()

                    if not user_illusts or not hasattr(
                        user_illusts, 'illusts'
                    ):
                        break

                    if not user_illusts.illusts:
                        break

                    new_count = 0
                    current_page_max_date = None

                    for item in user_illusts.illusts:
                        # 检查发布日期
                        post_date: datetime | None = None
                        if hasattr(item, 'create_date'):
                            # 记录原始日期用于调试
                            original_create_date = item.create_date
                            post_date = self._parse_create_date(
                                item.create_date
                            )

                            # 调试日志：显示日期转换
                            logger.debug(
                                f'Item {item.id}: '
                                f'original={original_create_date}, '
                                f'parsed={post_date}'
                            )

                            # 记录第一个作品的时间
                            if first_artwork_date is None and post_date:
                                first_artwork_date = post_date

                                # 如果第一个作品早于预设截止日期，调整截止日期
                                if post_date < initial_cutoff_date:
                                    actual_cutoff_date = (
                                        post_date
                                        - timedelta(days=backtrack_years * 365)
                                    )
                                    logger.info(
                                        f'调整 cutoff_date: '
                                        f'原始 {initial_cutoff_date} -> '
                                        f'调整后 {actual_cutoff_date} '
                                        f'(基于第一个作品 {post_date})'
                                    )

                            # 更新当前页最大日期
                            if (
                                current_page_max_date is None
                                or (
                                    post_date
                                    and post_date > current_page_max_date
                                )
                            ):
                                current_page_max_date = post_date

                            # 超过实际回采期限则停止
                            if post_date < actual_cutoff_date:
                                logger.info(
                                    f'Stopping at {post_date}, '
                                    f'before actual cutoff '
                                    f'{actual_cutoff_date}'
                                )
                                has_more = False
                                break

                        try:
                            artwork_pages = self._parse_artwork(item)
                            for artwork_data in artwork_pages:
                                artwork_data['collect_type'] = log_type
                                artworks_list.append(artwork_data)
                                new_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to parse artwork {item.id}: {e}"
                            )
                            continue

                    collected_count += new_count

                    # 使用当前页的最大日期更新全局最大日期
                    if current_page_max_date:
                        if (
                            last_artwork_date is None
                            or current_page_max_date > last_artwork_date
                        ):
                            last_artwork_date = current_page_max_date
                    else:
                        logger.warning(
                            f'{follow.user_name} '
                            f'page {page} has no valid dates'
                        )

                    # 检查是否还有更多
                    if not user_illusts.next_url:
                        has_more = False
                    else:
                        offset = self._parse_offset(user_illusts.next_url)

                    page += 1

                    # 批量等待
                    if self.limiter.batch_wait(page, 5):
                        logger.info("Pause in collect_single_user_artworks")

                except Exception as e:
                    logger.error(f"Error processing page {page}: {e}")
                    self.limiter.handle_error()
                    break

            # 批量保存作品
            saved_count = self._artwork_repo.batch_create(artworks_list)

            # 使用事务上下文合并更新
            if last_artwork_date:
                with self._follow_repo.with_session() as session:
                    # 重新查询获取 session 中的对象
                    instance = session.execute(
                        select(Follow).where(Follow.user_id == follow.user_id)
                    ).scalar_one_or_none()

                    if instance:
                        instance.last_artwork_date = last_artwork_date
                        instance.last_collect_date = get_utc_now()

                        if not instance.first_collect_date:
                            instance.first_collect_date = get_utc_now()

                        # 自动提交

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                f'Collected {saved_count} artworks from {follow.user_name}',
                saved_count
            )

            return {
                'success': True,
                'user_name': follow.user_name,
                'new_count': saved_count
            }

        except Exception as e:
            logger.error(f"Failed to collect user artworks: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def collect_all_follow_artworks(self) -> dict:
        """
        初始全量关注采集.

        Returns:
            采集结果
        """
        self._ensure_initialized()

        log_type = 'follow_user_artworks'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message='Starting initial follow collection'
        )

        try:
            # 获取回采年限配置
            backtrack_years = self.get_config_value(
                'new_user_backtrack_years', 2
            )

            # 获取所有关注用户
            follows = self._follow_repo.get_by_all()

            total_count = 0
            success_count = 0
            failed_users = []

            for follow in follows:
                try:
                    logger.info(f'start collecting for {follow.user_name}')
                    result = self.collect_single_user_artworks(
                        follow, backtrack_years
                    )
                    logger.info(
                        'collect %s: total %d artworks',
                        follow.user_name,
                        result['new_count']
                    )
                    total_count += result['new_count']
                    success_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to collect for {follow.user_name}: {e}"
                    )
                    failed_users.append(follow.user_name)

            # 更新日志
            message = (
                f'Collected {total_count} artworks '
                f'from {success_count}/{len(follows)} users'
            )
            if failed_users:
                message += f', Failed: {", ".join(failed_users)}'

            self._collection_repo.update_success(
                log.id, message, total_count
            )

            return {
                'success': True,
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': len(failed_users)
            }

        except Exception as e:
            logger.error(f"Failed to collect follow user artworks: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def collect_follow_new_works(self) -> dict:
        """
        采集关注用户新作品（使用illust_follow API）.
        如遇新用户，自动补充历史数据.

        Returns:
            采集结果
        """
        self._ensure_initialized()

        log_type = 'follow_new_works'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message='Starting follow new works collection'
        )

        try:
            self._ensure_valid_token()

            # 获取回采年限配置
            backtrack_years = self.get_config_value(
                'new_user_backtrack_years', 2
            )

            # 执行采集
            result = self._collect_follow_works(backtrack_years)

            # 批量保存作品
            saved_count = self._artwork_repo.batch_create(
                result['artworks_list']
            )

            # 构建日志消息
            message_parts = [
                f'Collected {saved_count} new artworks from follows'
            ]
            if result['new_users_count'] > 0:
                message_parts.append(
                    f', found {result["new_users_count"]} new users'
                )
            if result['backlog_artworks_count'] > 0:
                message_parts.append(
                    f', backlogged {result["backlog_artworks_count"]} artworks'
                )

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                ', '.join(message_parts),
                saved_count
            )

            return {
                'success': True,
                'total_new': saved_count,
                'new_users': result['new_users_count'],
                'backlogged_artworks': result['backlog_artworks_count']
            }

        except Exception as e:
            logger.error(f"Failed to collect follow new works: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def _collect_follow_works(
        self, backtrack_years: int
    ) -> dict:
        """
        采集关注用户新作品的主逻辑.

        Args:
            backtrack_years: 回采年限

        Returns:
            采集结果字典
        """
        artworks_list = []
        new_users_count = 0
        backlog_artworks_count = 0
        has_more = True
        offset = 0
        query_count = 1

        while has_more:
            try:
                # 获取一页数据
                follow_data = self._fetch_follow_page(offset)

                if follow_data is None:
                    break

                # 处理作品列表
                result = self._process_follow_works(
                    follow_data,
                    backtrack_years,
                    has_more
                )

                # 更新统计
                artworks_list.extend(result['artworks'])
                new_users_count += result['new_users_count']
                backlog_artworks_count += result['backlog_count']
                has_more = result['has_more']

                query_count += 1

                # 获取下一页 offset
                offset = self._parse_offset(follow_data.next_url)

                # 批量等待
                if self.limiter.batch_wait(query_count, 5):
                    logger.info("Pause in follow new works collection")

            except Exception as e:
                logger.error(f"Error processing page {query_count}: {e}")
                self.limiter.handle_error()
                break

        return {
            'artworks_list': artworks_list,
            'new_users_count': new_users_count,
            'backlog_artworks_count': backlog_artworks_count
        }

    def _fetch_follow_page(self, offset: int | str):
        """
        获取一页关注作品数据.

        Args:
            offset: 偏移量

        Returns:
            关注数据或None
        """
        follow_data = self.client.get_follow_illusts(
            offset=offset,
            restrict='public'
        )
        self.limiter.wait()

        # 验证返回数据
        if not follow_data or not hasattr(follow_data, 'illusts'):
            logger.warning("No illusts found in follow data")
            return None

        if not follow_data.illusts:
            logger.warning("Illusts is empty")
            return None

        logger.info(f"Follow new works count: {len(follow_data.illusts)}")
        return follow_data

    def _process_follow_works(
        self,
        follow_data,
        backtrack_years: int,
        has_more: bool
    ) -> dict:
        """
        处理一页关注作品.

        Args:
            follow_data: 关注数据
            backtrack_years: 回采年限
            has_more: 是否还有更多

        Returns:
            处理结果
        """
        artworks: list[Any] = []
        new_users_count = 0
        backlog_count = 0

        for item in follow_data.illusts:
            try:
                # 检查是否应该继续
                should_continue = self._should_process_artwork(item, has_more)
                if not should_continue:
                    return {
                        'artworks': artworks,
                        'new_users_count': new_users_count,
                        'backlog_count': backlog_count,
                        'has_more': False
                    }

                # 处理作品
                result = self._process_single_artwork(
                    item, backtrack_years
                )
                artworks.extend(result['artworks'])
                new_users_count += result['is_new']
                backlog_count += result['backlog_count']

            except Exception as e:
                logger.error(f"Failed to parse artwork {item.id}: {e}")
                continue

        return {
            'artworks': artworks,
            'new_users_count': new_users_count,
            'backlog_count': backlog_count,
            'has_more': has_more
        }

    def _should_process_artwork(self, item, has_more: bool) -> bool:
        """
        判断是否应该处理作品.

        Args:
            item: 作品项
            has_more: 是否还有更多

        Returns:
            是否应该处理
        """
        existing = self._artwork_repo.get_by_illust_id_and_page(
            item.id, 0
        )

        if not existing:
            return True

        # 检查作品类型
        collect_type = existing.collect_type

        if collect_type in ['follow_new_works', 'follow_user_artworks']:
            logger.info(
                f"作品 {item.id} 已存在（{collect_type}），停止采集"
            )
            return False

        if collect_type in [
            'daily_rank', 'weekly_rank', 'monthly_rank', 'ranking_works'
        ]:
            logger.info(
                f"作品 {item.id} 类型为 {collect_type}，"
                f"更新为 follow_new_works"
            )
            self._artwork_repo.update(
                existing.id,
                collect_type='follow_new_works'
            )
            return True

        logger.debug(
            f"作品 {item.id} 存在但来自 {collect_type}，跳过"
        )
        return False

    def _process_single_artwork(
        self, item, backtrack_years: int
    ) -> dict:
        """
        处理单个关注作品.

        Args:
            item: 作品项
            backtrack_years: 回采年限

        Returns:
            处理结果
        """
        # 解析作品
        artwork_pages = self._parse_artwork(item)
        user_id = item.user.id

        # 获取或创建用户
        follow = self._follow_repo.get_by_user_id(user_id)

        # 处理用户
        is_new, backlog_count = self._process_user_from_artwork(
            item, follow, backtrack_years
        )

        # 设置作品类型
        artworks = []
        for artwork_data in artwork_pages:
            artwork_data['collect_type'] = 'follow_new_works'
            artworks.append(artwork_data)

        return {
            'artworks': artworks,
            'is_new': is_new,
            'backlog_count': backlog_count
        }

    def _save_artwork_all_page(self, log_type, item) -> int:
        new_count = 0
        artwork_pages = self._parse_artwork(item)
        for artwork_data in artwork_pages:
            artwork_data['collect_type'] = log_type
            existing = self._artwork_repo.get_by_illust_id_and_page(
                item.id,
                artwork_data.get('page_index', 0)
            )
            if not existing:
                saved = self._artwork_repo.create(**artwork_data)
                if saved:
                    new_count += 1
        return new_count

    def _process_user_from_artwork(
        self,
        item,
        follow: Follow | None,
        backtrack_years: int
    ) -> tuple[bool, int]:
        """
        从作品项处理用户（更新或创建）.

        Args:
            item: 作品项
            follow: Follow对象或None
            backtrack_years: 回采年限

        Returns:
            (是否为新用户, 补充的作品数)
        """
        user_id = item.user.id

        if follow:
            # 使用事务上下文，所有操作在同一 session 中
            with self._follow_repo.with_session() as session:
                # 重新查询获取 session 中的对象
                instance = session.execute(
                    select(Follow).where(Follow.user_id == user_id)
                ).scalar_one_or_none()

                if not instance:
                    return (False, 0)

                # 更新基本信息
                instance.user_name = item.user.name
                if item.user.profile_image_urls:
                    instance.avatar_url = (
                        item.user.profile_image_urls.medium
                    )

                # 更新最后作品时间
                artwork_pages = self._parse_artwork(item)
                if artwork_pages:
                    artwork_date = artwork_pages[0]['post_date']
                    artwork_name = artwork_pages[0]['title']
                    logger.debug(
                        f'get {item.user.name} art_work:'
                        f'{artwork_name}-{artwork_date} '
                        f'record time:{instance.last_artwork_date}'
                    )
                    if (
                        instance.last_artwork_date is None
                        or artwork_date > instance.last_artwork_date
                    ):
                        instance.last_artwork_date = artwork_date

                # 更新采集时间
                instance.last_collect_date = get_utc_now()
                instance.updated_at = get_utc_now()

            return (False, 0)
        else:
            # 处理新用户
            logger.info(f"发现新用户: {item.user.name} (ID: {user_id})")
            backlog_count = 0

            try:
                # 创建 Follow 记录
                follow = self._follow_repo.create(
                    user_id=user_id,
                    user_name=item.user.name,
                    avatar_url=(
                        item.user.profile_image_urls.medium
                        if item.user.profile_image_urls
                        else None
                    ),
                    first_collect_date=get_utc_now(),
                    created_at=get_utc_now(),
                    updated_at=get_utc_now()
                )
                logger.info(f"已添加新用户: {item.user.name} (ID: {user_id})")

                # 补充历史数据
                try:
                    logger.info(f"开始补充历史数据: {item.user.name}")
                    result = self.collect_single_user_artworks(
                        follow, backtrack_years
                    )
                    backlog_count = result['new_count']
                    logger.info(
                        f"补充完成: {item.user.name}, "
                        f"新增 {result['new_count']} 个历史作品"
                    )
                except Exception as e:
                    logger.error(f"补充历史数据失败 {item.user.name}: {e}")

                return (True, backlog_count)

            except Exception as e:
                logger.error(f"创建新用户失败 {user_id}: {e}")
                return (False, 0)

    def update_artworks(self) -> dict:
        """
        更新作品元数据.

        Returns:
            更新结果
        """
        self._ensure_initialized()

        log_type = 'update_artworks'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message='Starting artwork metadata update'
        )

        try:
            # 确保token有效
            self._ensure_valid_token()

            # 获取需要更新的作品（有效，按last_updated_at升序）
            update_days = self.get_config_value('update_interval_days', 30)
            update_max_per_run = self.get_config_value(
                'update_max_per_run', 200
            )

            cutoff_date = get_utc_now() - timedelta(days=update_days)

            artworks = self._artwork_repo.get_artworks_for_update(
                post_date_start=cutoff_date,
                per_page=update_max_per_run
            )

            updated_count = 0

            for artwork in artworks:
                try:
                    # 获取作品详情
                    detail = self.client.get_illust_detail(artwork.illust_id)
                    self.limiter.wait()

                    if not detail or not hasattr(detail, 'illust'):
                        continue

                    item = detail.illust

                    # 更新书签数和浏览数
                    new_bookmarks = (
                        item.total_bookmarks
                        if hasattr(item, 'total_bookmarks') else 0
                    )
                    new_view = (
                        item.total_view
                        if hasattr(item, 'total_view') else 0
                    )

                    if (
                        new_bookmarks != artwork.total_bookmarks or
                        new_view != artwork.total_view
                    ):
                        self._artwork_repo.update(
                            artwork.id,
                            total_bookmarks=new_bookmarks,
                            total_view=new_view,
                            last_updated_at=get_utc_now()
                        )
                        updated_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to update artwork "
                        f"{artwork.illust_id}: {e}"
                    )
                    continue

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                f'Updated {updated_count} artworks',
                updated_count
            )

            return {
                'success': True,
                'updated_count': updated_count
            }

        except Exception as e:
            logger.error(f"Failed to update artworks: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def clean_up_old_logs(self) -> dict:
        """
        清理旧日志.

        Returns:
            清理结果
        """
        log_type = 'clean_up_logs'
        log = self._collection_repo.create_log(
            log_type=log_type,
            status='running',
            message='Starting log cleanup'
        )

        try:
            # 获取保留天数配置
            retention_days = self.get_config_value('log_retention_days', 90)

            # 执行清理
            deleted_count = self._collection_repo.delete_old_logs(
                retention_days
            )

            # 更新日志
            self._collection_repo.update_success(
                log.id,
                f'Deleted {deleted_count} old logs',
                deleted_count
            )

            return {
                'success': True,
                'deleted_count': deleted_count
            }

        except Exception as e:
            logger.error(f"Failed to cleanup logs: {e}")
            self._collection_repo.update_error(log.id, str(e))
            raise

    def _classify_content(self, item, tags: list) -> bool:
        """判断是否为R18内容."""
        is_r18 = False
        r18_keywords = ['R-18', 'R18', 'R-18G', 'R18G']
        for tag in tags:
            t = tag.upper()
            if any(k in t for k in r18_keywords):
                is_r18 = True
                break
        return is_r18
