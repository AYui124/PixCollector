"""Pixiv认证和Web认证模块."""
import logging
from datetime import datetime, timedelta

from flask_login import LoginManager, UserMixin
from pixivpy3 import ByPassSniApi

from database import db
from models import SystemConfig, User

logger = logging.getLogger(__name__)

# 创建Flask-Login实例
login_manager = LoginManager()
login_manager.login_view = 'web.web_login'
login_manager.login_message = ''


class WebUser(UserMixin):
    """Web用户包装器，用于Flask-Login."""

    def __init__(self, user: User):
        """
        初始化Web用户.

        Args:
            user: User模型实例
        """
        self.user = user

    def get_id(self) -> str:
        """返回用户ID."""
        return str(self.user.id)

    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证."""
        return True

    @property
    def is_active(self) -> bool:
        """检查是否活跃."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """检查是否匿名."""
        return False


@login_manager.user_loader
def load_user(user_id: int) -> WebUser | None:
    """
    根据ID加载用户.

    Args:
        user_id: 用户ID

    Returns:
        WebUser实例或None
    """
    user = db.session.get(User, int(user_id))
    if user:
        return WebUser(user)
    return None


class PixivAuthError(Exception):
    pass


class PixivAuth:
    """Pixiv认证管理器，使用ByPassSniApi."""

    def __init__(self):
        """初始化Pixiv认证管理器."""
        self._api = ByPassSniApi()
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.token_expires_at: datetime | None = None

    def _is_token_valid(self) -> bool:
        """
        检查当前token是否有效（存在且未过期）。

        注意：此方法不返回True，以便后续流程可以继续尝试刷新

        Returns:
            bool: 是否有效
        """
        if not self.access_token or not self.token_expires_at:
            return False

        # 提前5分钟判断为过期
        return datetime.now() < self.token_expires_at - timedelta(minutes=5)

    def _load_tokens_from_db(self) -> bool:
        """
        从数据库加载token到内存.

        注意：只负责加载，不做任何有效性判断
        即使没有access_token也要继续执行，确保能获取refresh_token

        Returns:
            bool: 是否至少加载到了refresh_token
        """
        load_success = True
        # 查询access_token
        access_config = db.session.query(SystemConfig).filter_by(
            config_key='access_token'
        ).first()
        if access_config and access_config.config_value:
            self.access_token = access_config.config_value
        else:
            logger.warning("No access_token found in database")

        # 查询refresh_token
        refresh_config = db.session.query(SystemConfig).filter_by(
            config_key='refresh_token'
        ).first()
        if refresh_config and refresh_config.config_value:
            self.refresh_token = refresh_config.config_value
        else:
            load_success = False
            logger.warning("No refresh_token found in database")

        # 查询token_expires_at
        expires_config = db.session.query(SystemConfig).filter_by(
            config_key='token_expires_at'
        ).first()
        if expires_config and expires_config.config_value:
            self.token_expires_at = datetime.strptime(
                expires_config.config_value,
                '%Y-%m-%d %H:%M:%S'
            )
        else:
            self.token_expires_at = None

        logger.info(f"Loaded tokens from database: {load_success}")
        return load_success

    def save_tokens(self, access_token: str, refresh_token: str) -> bool:
        """
        保存token到数据库.

        Args:
            access_token: 新的access_token
            refresh_token: 新的refresh_token

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存access_token
            access_config = db.session.query(SystemConfig).filter_by(
                config_key='access_token'
            ).first()
            if not access_config:
                access_config = SystemConfig(
                    config_key='access_token',
                    value_type='string'
                )
                db.session.add(access_config)
            access_config.config_value = access_token
            access_config.updated_at = datetime.now()

            # 保存refresh_token
            refresh_config = db.session.query(SystemConfig).filter_by(
                config_key='refresh_token'
            ).first()
            if not refresh_config:
                refresh_config = SystemConfig(
                    config_key='refresh_token',
                    value_type='string'
                )
                db.session.add(refresh_config)
            refresh_config.config_value = refresh_token
            refresh_config.updated_at = datetime.now()

            # 保存token_expires_at
            expires_config = db.session.query(SystemConfig).filter_by(
                config_key='token_expires_at'
            ).first()
            if not expires_config:
                expires_config = SystemConfig(
                    config_key='token_expires_at',
                    value_type='datetime'
                )
                db.session.add(expires_config)
            # access token通常1小时后过期
            expires_at = datetime.now() + timedelta(hours=1)
            expires_config.config_value = expires_at.strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            expires_config.updated_at = datetime.now()

            db.session.commit()

            self.access_token = access_token
            self.refresh_token = refresh_token
            self.token_expires_at = expires_at

            logger.info("Tokens saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            db.session.rollback()
            return False

    def refresh_access_token(self) -> bool:
        """
        使用refresh_token刷新access_token.

        Returns:
            bool: 是否刷新成功
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False

        try:
            # 使用refresh_token获取新的access_token
            self._api.auth(refresh_token=self.refresh_token)
            # 获取新的token
            new_access_token = self._api.access_token or ''
            new_refresh_token = self._api.refresh_token or ''

            # 保存新token
            return self.save_tokens(new_access_token, new_refresh_token)

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return False

    def ensure_authenticated(self) -> bool:
        """
        确保有有效的access_token.

        流程：
        1. 检查内存中access_token是否存在且未过期
        2. 没有：从数据库加载
        3. 加载后检查是否过期
        4. 过期：使用refresh_token刷新
        5. 没有refresh_token：返回False，停止API请求

        Returns:
            bool: 是否有有效token
        """
        # 检查当前token是否有效
        if self._is_token_valid():
            self._api.set_auth(self.access_token or '', self.refresh_token)
            return True

        # 从数据库加载
        if not self._load_tokens_from_db():
            return False

        # 检查加载的token是否有效
        if self._is_token_valid():
            self._api.set_auth(self.access_token or '', self.refresh_token)
            return True

        # token过期，尝试刷新
        if not self.refresh_token:
            logger.error("No refresh token available, cannot refresh")
            return False

        logger.info("Token expired, attempting to refresh...")
        if self.refresh_access_token():
            self._api.set_auth(self.access_token or '', self.refresh_token)
            return True

        return False

    def get_api(self) -> ByPassSniApi:
        """
        获取API实例.

        Returns:
            ByPassSniApi: API实例
        """
        return self._api


# 全局认证实例
pixiv_auth = PixivAuth()
