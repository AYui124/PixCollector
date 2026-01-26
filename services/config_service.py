"""配置Service."""
from datetime import datetime
from typing import Any, ClassVar

from repositories.config_repository import ConfigRepository


class ConfigService:
    """配置业务逻辑层."""

    _instance: ClassVar['ConfigService | None'] = None

    def __init__(self, config_repo: ConfigRepository):
        """
        初始化Service.

        Args:
            config_repo: 配置Repository
        """
        self.config_repo = config_repo
        self._cache: dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> 'ConfigService':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ConfigService实例
        """
        if cls._instance is None:
            config_repo = ConfigRepository.get_instance()
            cls._instance = cls(config_repo)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def _clear_cache(self, config_key: str | None = None) -> None:
        """
        清除配置缓存.

        Args:
            config_key: 配置键，None则清除所有
        """
        if config_key:
            # 清除单个配置缓存
            self._cache.pop(config_key, None)
        # 清除全部配置缓存
        self._cache.pop('all', None)

    def get_all_config(self) -> dict[str, Any]:
        """
        获取所有配置（带缓存和自动转换）.
        """
        # 检查缓存
        if 'all' in self._cache:
            cached: dict = self._cache['all']
            return cached

        with self.config_repo.get_session() as session:
            from sqlalchemy import select

            from models.system_config import SystemConfig

            configs = session.execute(
                select(SystemConfig)
            ).scalars().all()

            # 按value_type自动转换
            result: dict[str, Any] = {}
            for config in configs:
                result[config.config_key] = self._str_to_value(
                    config.config_value,
                    config.value_type
                )

            # 存入缓存
            self._cache['all'] = result
            return result

    def set_config(
        self, config_key: str, value: Any
    ) -> bool:
        """
        设置配置并清除缓存.

        Args:
            config_key: 配置键
            value: 配置值（自动转换类型）

        Returns:
            是否成功
        """
        # 转换为字符串并推断类型
        value_type = self._infer_value_type(value)
        value_str = self._value_to_str(value, value_type)

        # 保存到数据库（repo 内部完成所有操作）
        config = self.config_repo.set_config(config_key, value_str, value_type)

        # 清除相关缓存
        self._clear_cache(config_key)

        return config is not None

    def batch_set_config(self, config_data: dict) -> None:
        """
        批量设置配置.

        Args:
            config_data: 配置字典
        """
        for key, value in config_data.items():
            self.set_config(key, value)

    def save_tokens(
        self, access_token: str | None, refresh_token: str,
        user_id: int | None = None
    ) -> bool:
        """
        保存Token.

        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌
            user_id: 用户ID（可选）

        Returns:
            是否成功
        """
        success = True
        # 明确检查None，允许空字符串
        if access_token is not None:
            success = success and self.set_config(
                'access_token', access_token
            )
        success = success and self.set_config(
            'refresh_token', refresh_token
        )
        # 如果提供了user_id，也保存
        if user_id is not None:
            success = success and self.save_user_id(user_id)
        return success

    def save_user_id(self, user_id: int) -> bool:
        """
        保存用户ID.

        Args:
            user_id: 用户ID

        Returns:
            是否成功
        """
        return self.set_config('pixiv_user', user_id)

    def get_user_id(self) -> int | None:
        """
        获取用户ID（自动转换）.

        Returns:
            用户ID或None
        """
        # 直接从缓存获取（已自动转换）
        config = self.get_all_config()
        user_id = config.get('pixiv_user') or '0'
        return int(user_id)

    def clear_user_id(self) -> bool:
        """
        清空用户ID.

        Returns:
            是否成功
        """
        return self.set_config('pixiv_user', '')

    def get_token_expiry(self) -> datetime | None:
        """
        获取token过期时间（自动转换）.

        Returns:
            过期时间或None
        """
        # 直接从缓存获取（已自动转换）
        config = self.get_all_config()
        return config.get('token_expires_at')

    def set_token_expiry(self, expiry: datetime) -> bool:
        """
        设置token过期时间（自动类型判断）.

        Args:
            expiry: 过期时间

        Returns:
            是否成功
        """
        return self.set_config('token_expires_at', expiry)

    def _infer_value_type(
        self, value: str | int | float | bool | datetime | None
    ) -> str:
        """
        自动判断值的类型.

        Args:
            value: 值

        Returns:
            类型字符串
        """
        if value is None:
            return 'string'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, datetime):
            return 'datetime'
        else:
            return 'string'

    def _value_to_str(
        self, value: str | int | float | bool | datetime | None,
        value_type: str
    ) -> str | None:
        """
        将值转换为字符串存储.

        Args:
            value: 值
            value_type: 类型

        Returns:
            字符串值
        """
        if value is None:
            return None
        elif value_type == 'boolean':
            if not isinstance(value, bool):
                raise TypeError('Expected bool for boolean type')
            return 'true' if value else 'false'
        elif value_type == 'datetime':
            if not isinstance(value, datetime):
                raise TypeError('Expected datetime for datetime type')
            return value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return str(value)

    def _str_to_value(
        self, value_str: str | None, value_type: str
    ) -> str | int | float | bool | datetime | None:
        """
        将字符串按type转换为对应类型的值.

        Args:
            value_str: 字符串值
            value_type: 类型

        Returns:
            转换后的值
        """
        if value_str is None:
            return None
        elif value_type == 'integer':
            return int(value_str)
        elif value_type == 'float':
            return float(value_str)
        elif value_type == 'boolean':
            return value_str == 'true'
        elif value_type == 'datetime':
            return datetime.strptime(
                value_str, '%Y-%m-%d %H:%M:%S'
            )
        else:
            return value_str
