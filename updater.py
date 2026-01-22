"""作品元数据更新模块."""
import logging
from datetime import datetime, timedelta

from pixivpy3 import ByPassSniApi

from auth import PixivAuthError, pixiv_auth
from database import db
from models import Artwork, CollectionLog, SystemConfig
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ArtworkUpdater:
    """作品元数据更新器."""

    def __init__(self, rate_limiter: RateLimiter):
        """
        初始化更新器.

        Args:
            rate_limiter:速率限制器实例
        """
        self._api = pixiv_auth.get_api()
        self.rate_limiter = rate_limiter

    def api(self, needAuth: bool = True) -> ByPassSniApi:
        if needAuth and pixiv_auth.ensure_authenticated():
            return self._api
        if needAuth is False:
            return self._api
        raise PixivAuthError('Token authenticate failed')

    def _get_config_dict(self) -> dict:
        """从SystemConfig获取配置字典."""
        config_items = db.session.query(SystemConfig).all()
        config_dict = {}
        for item in config_items:
            config_dict[item.config_key] = item.to_dict()['value']
        return config_dict

    def update_artworks(self) -> dict:
        """
        批量更新作品元数据（分页游标 + batch commit）

        优化点：
        1. 缓存配置避免重复查询
        2. 批量提交减少数据库操作
        3. 使用分页游标流式处理避免内存问题
        4. 预加载关联数据避免 N+1 查询
        5. 添加进度反馈

        Returns:
            Dict: 更新结果统计
        """
        log = CollectionLog(
            log_type='update_artworks',
            status='running',
            message='Starting artwork metadata update'
        )
        db.session.add(log)
        db.session.commit()

        try:
            # 缓存配置，避免重复查询
            config_dict = self._get_config_dict()
            if not config_dict:
                logger.warning("No system config found, using defaults")
                config_dict = {}

            update_interval = config_dict.get('update_interval_days', 7)
            max_per_run = config_dict.get('update_max_per_run', 200)

            # 获取需要更新的作品总数
            cutoff_date = datetime.now() - timedelta(days=update_interval)
            artworks = (
                db.session.query(Artwork)
                .filter(Artwork.last_updated_at < cutoff_date)
                .filter_by(is_valid=True)
                .filter_by(page_index=0)
                .order_by(Artwork.last_updated_at, Artwork.id)
                .limit(max_per_run)
                .all()
            )
            total_count = len(artworks)
            results = {'successed': 0, 'failed': 0, 'invalid': 0}
            logger.info(f"Current got {total_count} artworks to update")

            if not artworks:
                log.status = 'success'
                log.artworks_count = results['successed']
                log.message = 'No artwork metadata need to update'
                db.session.commit()
                return results  # 已处理完所有作品
            illust_ids = []
            for i, artwork in enumerate(artworks, 1):
                try:
                    if artwork.illust_id in illust_ids:
                        results['successed'] += 1
                        continue
                    illust_ids.append(artwork.illust_id)
                    # 更新单个作品（传入缓存的配置）
                    success = self._update_single_artwork(
                        artwork, config_dict=config_dict
                    )

                    if success:
                        results['successed'] += 1
                    else:
                        results['invalid'] += 1
                    if i % 20 == 0:
                        db.session.commit()
                        self.rate_limiter.wait()
                        logger.info(f'update_artworks 进度：{i}/{total_count}')
                except Exception as e:
                    logger.error(
                        "Failed to update "
                        f"{artwork.illust_id}: {e}"
                    )
                    results['failed'] += 1
            logger.info('update_artworks 进度：100%')
            # 更新日志
            log.status = 'success'
            log.message = (
                f"Updated {results['successed']} artworks, "
                f"failed {results['failed']}, "
                f"marked {results['invalid']} as invalid. "
                f"Processed {total_count} total."
            )
            log.artworks_count = results['successed']
            db.session.commit()

            return results

        except Exception as e:
            logger.error(f"Failed to update artworks: {e}")
            log.status = 'failed'
            log.message = f"Failed to update artworks: {e}"
            db.session.commit()
            raise

    def _update_single_artwork(
        self,
        artwork: Artwork,
        config_dict: dict | None = None
    ) -> bool:
        """
        更新单个作品的元数据（更新该作品的所有页）.

        Args:
            artwork: Artwork实例（可以是该作品的任意一页）
            config_dict: 缓存的配置字典，避免重复查询

        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取作品详情
            detail = self.api().illust_detail(artwork.illust_id)
            self.rate_limiter.wait()

            if not detail or not detail.illust:
                logger.warning(
                    f"Artwork {artwork.illust_id} not found"
                )
                # 标记该作品的所有页为失效
                self._mark_invalid_all_pages(
                    artwork.illust_id,
                    "Artwork not found",
                    config_dict=config_dict
                )
                return False

            item = detail.illust

            # 获取该作品的所有页
            all_pages = db.session.query(Artwork).filter_by(
                illust_id=artwork.illust_id
            ).all()

            if not all_pages:
                logger.warning(
                    f"No pages found for artwork {artwork.illust_id}"
                )
                return False

            # 更新该作品的每一页
            for page_artwork in all_pages:
                # 更新元数据
                page_artwork.title = item.title
                page_artwork.author_id = item.user.id
                page_artwork.author_name = item.user.name
                page_artwork.page_count = (
                    item.page_count
                    if hasattr(item, 'page_count') else 1
                )
                page_artwork.total_bookmarks = (
                    item.total_bookmarks
                    if hasattr(item, 'total_bookmarks') else 0
                )
                page_artwork.total_view = (
                    item.total_view
                    if hasattr(item, 'total_view') else 0
                )

                # 更新分享URL
                page_artwork.share_url = (
                    f"https://www.pixiv.net/artworks/{item.id}"
                )

                # 更新标签
                if hasattr(item, 'tags'):
                    page_artwork.tags = [tag.name for tag in item.tags]

                # 更新R18标识
                if hasattr(item, 'sanity_level'):
                    page_artwork.is_r18 = item.sanity_level in [4, 6]

                # 更新URL（验证有效性）
                if item.image_urls and item.image_urls.large:
                    # 多图作品使用对应的页URL
                    if (hasattr(item, 'meta_pages')
                            and item.meta_pages
                            and page_artwork.page_index
                            < len(item.meta_pages)):
                        page_artwork.url = (
                            item.meta_pages[page_artwork.page_index]
                            .image_urls.large
                        )
                    else:
                        page_artwork.url = item.image_urls.large

                    page_artwork.is_valid = True
                    page_artwork.error_message = None
                else:
                    self._mark_invalid(
                        page_artwork,
                        "No valid image URL",
                        config_dict=config_dict
                    )
                    return False

                page_artwork.last_updated_at = datetime.now()

            # 不在这里提交，由调用者批量提交
            logger.debug(
                f"Updated {len(all_pages)} pages for artwork "
                f"{artwork.illust_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error updating artwork {artwork.illust_id}: {e}"
            )

            # 标记该作品的所有页为失效
            error_msg = str(e)
            if '404' in error_msg or 'not found' in error_msg.lower():
                self._mark_invalid_all_pages(
                    artwork.illust_id,
                    "Artwork not found",
                    config_dict=config_dict
                )
            else:
                self._mark_invalid_all_pages(
                    artwork.illust_id,
                    f"Update error: {error_msg}",
                    config_dict=config_dict
                )

            return False

    def _mark_invalid(
        self,
        artwork: Artwork,
        message: str,
        config_dict: dict | None = None
    ) -> None:
        """
        标记单个作品为失效.

        Args:
            artwork: Artwork实例
            message: 失效原因
            config_dict: 缓存的配置字典，避免重复查询
        """
        if config_dict is None:
            config_dict = self._get_config_dict()

        action = config_dict.get('invalid_artwork_action', 'mark')

        if action == 'delete':
            logger.info(
                f"Deleting invalid artwork {artwork.illust_id}"
            )
            db.session.delete(artwork)
        elif action == 'keep':
            logger.info(
                f"Keeping invalid artwork {artwork.illust_id}"
            )
            artwork.is_valid = False
            artwork.error_message = message
        else:  # mark
            artwork.is_valid = False
            artwork.error_message = message

        # 不在这里提交，由调用者批量提交

    def _mark_invalid_all_pages(
        self,
        illust_id: int,
        message: str,
        config_dict: dict | None = None
    ) -> None:
        """
        标记某个作品的所有页为失效.

        Args:
            illust_id: 作品ID
            message: 失效原因
            config_dict: 缓存的配置字典，避免重复查询
        """
        if config_dict is None:
            config_dict = self._get_config_dict()

        action = config_dict.get('invalid_artwork_action', 'mark')

        # 获取该作品的所有页
        all_pages = db.session.query(
            Artwork
        ).filter_by(illust_id=illust_id).all()

        if action == 'delete':
            logger.info(
                f"Deleting all {len(all_pages)} pages "
                f"of artwork {illust_id}"
            )
            for page in all_pages:
                db.session.delete(page)
        elif action == 'keep':
            logger.info(
                f"Keeping all {len(all_pages)} pages "
                f"of artwork {illust_id}"
            )
            for page in all_pages:
                page.is_valid = False
                page.error_message = message
        else:  # mark
            for page in all_pages:
                page.is_valid = False
                page.error_message = message

        # 不在这里提交，由调用者批量提交
