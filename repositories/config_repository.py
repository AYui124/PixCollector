"""配置Repository（SQLAlchemy 2.0）."""
from datetime import datetime
from typing import ClassVar

from sqlalchemy import select

from models.system_config import SystemConfig
from repositories.base_repository import BaseRepository


class ConfigRepository(BaseRepository[SystemConfig]):
    """配置数据访问层."""

    _instance: ClassVar['ConfigRepository | None'] = None

    def __init__(self):
        super().__init__(SystemConfig)

    @classmethod
    def get_instance(cls) -> 'ConfigRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            ConfigRepository实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def get_by_key(self, config_key: str) -> SystemConfig | None:
        """
        根据键获取配置.

        Args:
            config_key: 配置键

        Returns:
            配置实例或None
        """
        with self.get_session() as session:
            return session.execute(
                select(SystemConfig).where(
                    SystemConfig.config_key == config_key
                )
            ).scalar_one_or_none()

    def get_all_config_dict(self) -> dict[str, str | None]:
        """
        获取所有配置为字典（字符串值）.

        Returns:
            配置字典
        """
        with self.get_session() as session:
            configs = session.execute(
                select(SystemConfig)
            ).scalars().all()

            return {item.config_key: item.config_value for item in configs}

    def set_config(
        self,
        config_key: str,
        value: str | None,
        value_type: str = 'string'
    ) -> SystemConfig | None:
        """
        设置配置.

        Args:
            config_key: 配置键
            value: 配置值（字符串）
            value_type: 值类型

        Returns:
            配置实例或None
        """
        with self.get_session() as session:
            config: SystemConfig | None = session.execute(
                select(SystemConfig).where(
                    SystemConfig.config_key == config_key
                )
            ).scalar_one_or_none()

            if config:
                config.config_value = value
                config.value_type = value_type
                session.flush()
                session.refresh(config)
                return config
            else:
                # 创建新配置时同时设置 value_type
                new_config = SystemConfig(
                    id=0,  # 将由数据库自动分配
                    config_key=config_key,
                    config_value=value,
                    value_type=value_type,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(new_config)
                session.flush()
                session.refresh(new_config)
                return new_config
