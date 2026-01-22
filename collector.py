"""Pixiv数据采集模块."""
import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from pixivpy3 import ByPassSniApi

from auth import PixivAuthError, pixiv_auth
from database import db
from models import Artwork, CollectionLog, Follow, SystemConfig
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_RANK_MODE = Literal[
    "day",
    "week",
    "month",
    "",
]


class PixivCollector:
    """Pixiv数据采集器."""

    def __init__(self, rate_limiter: RateLimiter):
        """
        初始化采集器.

        Args:
            rate_limiter: 速率限制器实例
        """
        self._api = pixiv_auth.get_api()
        self.rate_limiter = rate_limiter

    def api(self, needAuth: bool = True) -> ByPassSniApi:
        if needAuth and pixiv_auth.ensure_authenticated():
            return self._api
        if needAuth is False:
            return self._api
        raise PixivAuthError('Token authenticate failed')

    def user(self) -> int | str:
        if self.api().user_id == 0:
            pixiv_auth.refresh_access_token()
        return self.api().user_id

    def _validate_api_response(
        self,
        response,
        expected_attr: str | None = None
    ) -> bool:
        """
        验证API响应数据.

        Args:
            response: API响应对象
            expected_attr: 期望存在的属性名

        Returns:
            bool: 是否有效
        """
        if response is None:
            return False

        if expected_attr:
            return (
                hasattr(response, expected_attr)
                and getattr(response, expected_attr) is not None
            )

        return True

    def _parse_pagination_offset(
        self, next_url: str | None
    ) -> int | str | None:
        """
        解析分页offset.

        Args:
            next_url: 下一页URL

        Returns:
            offset值或None
        """
        if not next_url:
            return None

        next_qs = self.api(False).parse_qs(next_url)
        return str(next_qs.get('offset') or 0) if next_qs else None

    def _create_log(self, log_type: str, message: str) -> CollectionLog:
        """
        创建并保存采集日志.

        Args:
            log_type: 日志类型
            message: 日志消息

        Returns:
            CollectionLog: 日志对象
        """
        log = CollectionLog(
            log_type=log_type,
            status='running',
            message=message
        )
        db.session.add(log)
        db.session.commit()
        return log

    def _update_log_success(
        self, log: CollectionLog, message: str, count: int | None = None
    ):
        """
        更新成功日志.

        Args:
            log: 日志对象
            message: 成功消息
            count: 作品数量
        """
        log.status = 'success'
        log.message = message
        if count is not None:
            log.artworks_count = count
        db.session.commit()

    def _update_log_error(self, log: CollectionLog, error: str):
        """
        更新失败日志.

        Args:
            log: 日志对象
            error: 错误信息
        """
        log.status = 'failed'
        log.message = error
        db.session.commit()

    def _get_backtrack_years(self) -> int:
        """
        获取回采年限配置.

        Returns:
            int: 回采年限
        """
        config = db.session.query(SystemConfig).filter_by(
            config_key='new_user_backtrack_years'
        ).first()
        if not config:
            return 2
        year = config.int_value()
        return year or 2

    def _get_log_retention_days(self) -> int:
        """
        获取采集日志保留日志.

        Returns:
            int: 保留天数
        """
        config = db.session.query(SystemConfig).filter_by(
            config_key='log_retention_days'
        ).first()
        if not config:
            return 30
        days = config.int_value()
        return days or 30

    def _collect_rank(self, mode: _RANK_MODE, log_type: str) -> dict:
        """
        通用排行榜采集方法.

        Args:
            mode: 排行榜模式 (day/week/month)
            log_type: 日志类型

        Returns:
            Dict: 采集结果统计
        """
        log = self._create_log(log_type, f'Starting {log_type} collection')

        try:
            artworks_list = []

            # 获取排行榜数据
            logger.info(f"Fetching {mode} ranking...")
            rank_data = self.api().illust_ranking(mode=mode)
            self.rate_limiter.wait()

            # 验证返回数据
            if not self._validate_api_response(rank_data, 'illusts'):
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
            saved_count = self._save_artworks(artworks_list)

            # 更新日志
            self._update_log_success(
                log,
                f'Collected {saved_count} artworks from {log_type}',
                saved_count
            )

            return {'success': True, 'count': saved_count}

        except Exception as e:
            logger.error(f"Failed to collect {log_type}: {e}")
            self._update_log_error(log, str(e))
            raise

    def collect_daily_rank(self) -> dict:
        """
        采集每日排行榜前30作品.

        Returns:
            Dict: 采集结果统计
        """
        return self._collect_rank('day', 'ranking_works')

    def collect_weekly_rank(self) -> dict:
        """
        采集每周排行榜前30作品.

        Returns:
            Dict: 采集结果统计
        """
        return self._collect_rank('week', 'ranking_works')

    def collect_monthly_rank(self) -> dict:
        """
        采集每月排行榜前30作品.

        Returns:
            Dict: 采集结果统计
        """
        return self._collect_rank('month', 'ranking_works')

    def sync_follows(self) -> dict:
        """
        同步关注列表.

        Returns:
            Dict: 同步结果统计
        """
        log = self._create_log('follow_new_follow', 'Starting follow sync')

        try:
            new_follows = 0
            has_more = True
            offset: int | str | None = 0
            queryCount = 1

            while has_more:
                try:
                    # 获取关注列表
                    follows_data = self.api().user_following(
                        self.user(),
                        offset=offset
                    )
                    self.rate_limiter.wait()

                    # 验证返回数据
                    if not self._validate_api_response(
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
                        user_id = user_info.user.id
                        existing = db.session.query(Follow).filter_by(
                            user_id=user_id
                        ).first()

                        if not existing:
                            # 新关注用户
                            follow = Follow(
                                user_id=user_id,
                                user_name=user_info.user.name,
                                avatar_url=(
                                    user_info.user.profile_image_urls.medium
                                    if user_info.user.profile_image_urls
                                    else None
                                ),
                                first_collect_date=datetime.now()
                            )
                            db.session.add(follow)
                            new_follows += 1
                            logger.info(f"New follow: {user_info.user.name}")
                        else:
                            # 已存在，说明已到达上次同步位置，停止继续分页
                            logger.info(
                                f"已存在用户 {user_info.user.name}，"
                                f"停止同步"
                            )
                            has_more = False
                            break

                    # 每页处理完后立即提交数据库
                    db.session.commit()

                    queryCount += 1

                    # 检查是否还有更多
                    offset = self._parse_pagination_offset(
                        follows_data.next_url
                    )
                    if offset is None:
                        has_more = False

                    # 批量等待
                    if self.rate_limiter.batch_wait(queryCount, interval=5):
                        logger.info("Pause in sync_follows")

                except Exception as e:
                    logger.error(f"Error processing page {queryCount}: {e}")
                    self.rate_limiter.handle_error()
                    # 出错时也提交已处理的数据
                    db.session.commit()
                    break

            # 更新日志
            self._update_log_success(
                log,
                f'Synced {new_follows} new follows'
            )

            return {'success': True, 'new_follows': new_follows}

        except Exception as e:
            logger.error(f"Failed to sync follows: {e}")
            self._update_log_error(log, str(e))
            raise

    def collect_follow_user_artworks(self) -> dict:
        """
        初始全量关注采集 - 遍历所有关注用户采集作品.

        Returns:
            Dict: 采集结果统计
        """
        log = self._create_log(
            'follow_user_artworks',
            'Starting follow user artworks collection'
        )

        try:
            follows = db.session.query(Follow).all()
            logger.info(f"Found {len(follows)} followed users")

            total_new = 0
            total_processed = 0
            backtrack_years = self._get_backtrack_years()

            for follow in follows:
                try:
                    result = self.collect_user_artworks(
                        follow, backtrack_years, True
                    )
                    total_new += result['new_count']
                    total_processed += 1

                    logger.info(
                        f"User {follow.user_name}: "
                        f"{result['new_count']} new artworks"
                    )

                    # 批量等待
                    if self.rate_limiter.batch_wait(total_processed, 5):
                        logger.info("Batch pause in works collection")

                except Exception as e:
                    logger.error(
                        f"Failed to collect for {follow.user_id}: {e}"
                    )
                    continue

            # 更新日志
            self._update_log_success(
                log,
                f'Collected {total_new} artworks from {total_processed} users',
                total_new
            )

            return {
                'success': True,
                'total_new': total_new,
                'total_processed': total_processed
            }

        except Exception as e:
            logger.error(f"Failed to collect follow user artworks: {e}")
            self._update_log_error(log, str(e))
            raise

    def collect_user_artworks(
        self,
        follow: Follow,
        backtrack_years: int,
        ignore_early_collect: bool
    ) -> dict:
        """
        采集单个用户的作品.

        Args:
            follow: Follow实例
            backtrack_years: 新用户回采年数

        Returns:
            Dict: 采集结果
        """
        new_count = 0
        last_artwork_date = None
        has_more = True
        offset: int | str | None = 0

        # 计算起始时间
        if not ignore_early_collect and follow.last_collect_date:
            start_time = datetime(
                follow.last_collect_date.year,
                follow.last_collect_date.month,
                follow.last_collect_date.day
            )
        else:
            now = datetime.now()
            start_time = datetime(now.year - backtrack_years, 1, 1)
        logger.info(
            'collect_user_artworks: %s, start:%s',
            follow.user_name,
            start_time
        )
        while has_more:
            try:
                user_artworks = self.api().user_illusts(
                    follow.user_id,
                    offset=offset,
                    type='illust'
                )
                self.rate_limiter.wait()

                # 验证返回数据
                if not self._validate_api_response(user_artworks, 'illusts'):
                    logger.warning(
                        f"No artworks found for user {follow.user_id}"
                    )
                    break

                if not user_artworks.illusts:
                    has_more = False
                    break

                # 处理每个作品
                for item in user_artworks.illusts:
                    artwork_pages = self._parse_artwork(item)

                    # 更新最后作品时间
                    artwork_date = (
                        artwork_pages[0]['post_date']
                        if artwork_pages
                        else None
                    )

                    # 超过年限则停止
                    if artwork_date and artwork_date < start_time:
                        has_more = False
                        break
                    # 检查是否已存在
                    existing = db.session.query(Artwork).filter_by(
                            illust_id=item.id,
                            page_index=0
                        ).first()
                    if not ignore_early_collect and existing:
                        logger.info(f"Artwork {item.id} exists, stopping")
                        has_more = False
                        break

                    # 保存作品
                    if not existing:
                        for artwork_data in artwork_pages:
                            artwork_data['collect_type'] = 'follow_new_works'
                            db.session.add(Artwork(**artwork_data))
                            new_count += 1

                    # 更新最后作品时间
                    if (
                        last_artwork_date is None
                        or artwork_date > last_artwork_date
                    ):
                        last_artwork_date = artwork_date

                # 检查是否还有更多
                offset = self._parse_pagination_offset(user_artworks.next_url)
                if offset is None:
                    has_more = False

            except Exception as e:
                logger.error(f"Error collecting user artworks: {e}")
                self.rate_limiter.handle_error()
                break

        # 更新follow记录
        if last_artwork_date:
            follow.last_artwork_date = last_artwork_date

        follow.last_collect_date = datetime.now()
        follow.updated_at = datetime.now()
        db.session.commit()

        return {'new_count': new_count}

    def _parse_artwork(self, item) -> list[dict]:
        """
        解析作品数据，返回多图作品的所有页.

        Args:
            item: Pixiv API返回的作品项

        Returns:
            List[Dict]: 解析后的作品数据列表（每页一条）
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
        rank_date = None
        post_date = None
        if hasattr(item, 'create_date'):
            # 解析创作时间（保留时区，转换为UTC存储）
            post_date_with_tz = datetime.strptime(
                item.create_date,
                '%Y-%m-%dT%H:%M:%S%z'
            )
            # 转换为UTC时间存储
            post_date = post_date_with_tz.astimezone(UTC).replace(tzinfo=None)
            # 排行榜日期只需要日期部分（转换为本地时间）
            rank_date = post_date_with_tz.astimezone().date()

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
        is_vaild = artwork_type == 'illust' and '漫画' not in tags
        err_msg = (
            artwork_type if artwork_type != 'illust' else 'Not like'
        )
        if hasattr(item, 'meta_pages') and item.meta_pages:
            # 多图作品
            for page_index in range(page_count):
                # 从meta_pages获取图片URL
                if page_index < len(item.meta_pages):
                    page_url = item.meta_pages[page_index].image_urls.large
                else:
                    # 如果meta_pages不完整，使用主图
                    page_url = item.image_urls.large if item.image_urls else ''

                artworks_list.append({
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
                        item.total_view if hasattr(item, 'total_view') else 0
                    ),
                    'rank': rank,
                    'rank_date': rank_date,
                    'post_date': post_date,
                    'tags': tags,
                    'is_r18': is_r18,
                    'type': artwork_type,
                    'is_valid': is_vaild,
                    'error_message': err_msg,
                    'last_updated_at': post_date,
                })
        else:
            # 单图作品
            artworks_list.append({
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
                    item.total_view if hasattr(item, 'total_view') else 0
                ),
                'rank': rank,
                'rank_date': rank_date,
                'post_date': post_date,
                'tags': tags,
                'is_r18': is_r18,
                'type': artwork_type,
                'is_valid': is_vaild,
                'error_message': err_msg,
                'last_updated_at': post_date,  # 设置为创作时间，避免集中更新
            })

        return artworks_list

    def _classify_content(self, item, tags) -> bool:
        is_r18 = False
        r18_keywords = ['R-18', 'R18', 'R-18G', 'R18G']
        for tag in tags:
            t = tag.upper()
            if any(k in t for k in r18_keywords):
                is_r18 = True

        return is_r18

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
            # 更新现有用户
            follow.user_name = item.user.name
            profile_urls = item.user.profile_image_urls
            if profile_urls:
                follow.avatar_url = profile_urls.medium

            # 更新最后作品时间
            artwork_pages = self._parse_artwork(item)
            if artwork_pages:
                artwork_date = artwork_pages[0]['post_date']
                if (
                    follow.last_artwork_date is None
                    or artwork_date > follow.last_artwork_date
                ):
                    follow.last_artwork_date = artwork_date

            follow.last_collect_date = datetime.now()
            follow.updated_at = datetime.now()
            return (False, 0)
        else:
            # 处理新用户
            logger.info(f"发现新用户: {item.user.name} (ID: {user_id})")
            backlog_count = 0

            try:
                # 创建 Follow 记录
                follow = Follow(
                    user_id=user_id,
                    user_name=item.user.name,
                    avatar_url=(
                        item.user.profile_image_urls.medium
                        if item.user.profile_image_urls
                        else None
                    ),
                    first_collect_date=datetime.now(),
                    last_collect_date=None,
                    last_artwork_date=None
                )
                db.session.add(follow)
                db.session.flush()

                logger.info(f"已添加新用户: {item.user.name} (ID: {user_id})")

                # 补充历史数据
                try:
                    logger.info(f"开始补充历史数据: {item.user.name}")
                    result = self.collect_user_artworks(
                        follow, backtrack_years, False
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

    def collect_follow_works(self) -> dict:
        """
        采集关注用户新作品（使用illust_follow API）.
        如遇新用户，自动补充历史数据.

        Returns:
            Dict: 采集结果统计
        """
        log = self._create_log(
            'follow_new_works',
            'Starting follow new works collection'
        )

        try:
            artworks_list = []
            new_users_count = 0
            backlog_artworks_count = 0
            has_more = True
            offset: int | str | None = 0
            queryCount = 1
            backtrack_years = self._get_backtrack_years()

            while has_more:
                try:
                    # 获取关注用户新作品
                    follow_data = self.api().illust_follow(
                        restrict='public',
                        offset=offset
                    )
                    self.rate_limiter.wait()

                    # 验证返回数据
                    if not self._validate_api_response(follow_data, 'illusts'):
                        logger.warning("No illusts found in follow data")
                        break

                    if not follow_data.illusts:
                        logger.warning("Illusts is empty")
                        has_more = False
                        break

                    logger.info(
                        f"Follow new works count: {len(follow_data.illusts)}"
                    )

                    # 处理每个作品（按时间降序）
                    for item in follow_data.illusts:
                        try:
                            # 先检查作品是否已存在（检查第一页）
                            existing = db.session.query(Artwork).filter_by(
                                illust_id=item.id,
                                page_index=0
                            ).first()

                            if existing:
                                # 检查该作品是否来自关注采集
                                if existing.collect_type in [
                                    'follow_new_works',
                                    'follow_user_artworks'
                                ]:
                                    # 是关注采集的作品，已到上次采集位置，停止
                                    logger.info(
                                        f"作品 {item.id} 已存在"
                                        f"（{existing.collect_type}） "
                                        f"停止采集 "
                                    )
                                    has_more = False
                                    break
                                elif existing.collect_type in [
                                    'daily_rank',
                                    'weekly_rank',
                                    'monthly_rank',
                                    'ranking_works'
                                ]:
                                    # 是排行榜采集的作品，更新为关注新作品类型
                                    logger.info(
                                        f"作品 {item.id} 类型为"
                                        f" {existing.collect_type}，"
                                        f"更新为 follow_new_works"
                                    )
                                    existing.collect_type = 'follow_new_works'
                                    # 继续处理，不停止
                                else:
                                    # 其他类型（如 update_artworks），跳过
                                    logger.debug(
                                        f"作品 {item.id} 存在但来自 "
                                        f"{existing.collect_type}，跳过"
                                    )
                                    continue

                            # 作品不存在，继续处理
                            artwork_pages = self._parse_artwork(item)
                            user_id = item.user.id

                            # 获取或创建用户
                            follow = db.session.query(Follow).filter_by(
                                user_id=user_id
                            ).first()

                            # 处理用户（更新或新建）
                            is_new, backlog_count = (
                                self._process_user_from_artwork(
                                    item, follow, backtrack_years
                                )
                            )

                            if is_new:
                                new_users_count += 1
                            backlog_artworks_count += backlog_count

                            # 添加作品到列表
                            for artwork_data in artwork_pages:
                                artwork_data['collect_type'] = (
                                    'follow_new_works'
                                )
                                artworks_list.append(artwork_data)

                        except Exception as e:
                            logger.error(
                                f"Failed to parse artwork {item.id}: {e}"
                            )
                            continue

                    queryCount += 1

                    # 检查是否还有更多
                    offset = self._parse_pagination_offset(
                        follow_data.next_url
                    )
                    if offset is None:
                        has_more = False

                    # 批量等待
                    if self.rate_limiter.batch_wait(queryCount, interval=5):
                        logger.info("Pause in follow new works collection")

                except Exception as e:
                    logger.error(f"Error processing page {queryCount}: {e}")
                    self.rate_limiter.handle_error()
                    break

            # 批量保存作品
            saved_count = self._save_artworks(artworks_list)

            # 构建日志消息
            message_parts = [
                f'Collected {saved_count} new artworks from follows'
            ]
            if new_users_count > 0:
                message_parts.append(
                    f', found {new_users_count} new users'
                )
            if backlog_artworks_count > 0:
                message_parts.append(
                    f', backlogged {backlog_artworks_count} artworks'
                )

            # 更新日志
            self._update_log_success(
                log,
                ', '.join(message_parts),
                saved_count
            )

            return {
                'success': True,
                'total_new': saved_count,
                'new_users': new_users_count,
                'backlogged_artworks': backlog_artworks_count
            }

        except Exception as e:
            logger.error(f"Failed to collect follow new works: {e}")
            self._update_log_error(log, str(e))
            raise

    def _save_artworks(self, artworks_list: list[dict]) -> int:
        """
        批量保存作品，去重处理（基于illust_id + page_index）.

        Args:
            artworks_list: 作品数据列表

        Returns:
            int: 实际保存数量
        """
        saved_count = 0
        for artwork_data in artworks_list:
            illust_id = artwork_data['illust_id']
            page_index = artwork_data.get('page_index', 0)

            # 基于illust_id和page_index去重
            existing = db.session.query(Artwork).filter_by(
                illust_id=illust_id,
                page_index=page_index
            ).first()

            if not existing:
                artwork = Artwork(**artwork_data)
                db.session.add(artwork)
                saved_count += 1

        db.session.commit()
        return saved_count

    def clean_up_old_logs(self) -> dict:
        """
        清理指定天数前的采集日志.

        Args:
            retention_days: 保留天数

        Returns:
            Dict: 清理结果统计
        """
        log = self._create_log(
            'cleanup_logs',
            'Starting clean up'
        )
        try:
            retention_days = self._get_log_retention_days()

            # 计算截止时间
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # 查询需要删除的日志
            old_logs = db.session.query(CollectionLog).filter(
                CollectionLog.created_at < cutoff_date
            ).all()

            deleted_count = len(old_logs)

            if deleted_count == 0:
                message = (
                    f'No logs to clean up '
                    f'that are older than {retention_days} days'
                )
                self._update_log_success(log, message, 0)
                return {'success': True, 'deleted_count': 0}

            # 删除旧日志
            for old_log in old_logs:
                db.session.delete(old_log)

            db.session.commit()

            # 更新日志
            message = (
                f'Cleaned up {deleted_count} logs '
                f'older than {retention_days} days'
            )
            self._update_log_success(log, message, deleted_count)

            logger.info(
                f"Cleaned completed: delete {deleted_count} logs "
                f"that are older than {retention_days} days"
            )

            return {'success': True, 'deleted_count': deleted_count}

        except Exception as e:
            logger.error(f"Failed to clean up old logs: {e}")
            self._update_log_error(log, str(e))
            raise
