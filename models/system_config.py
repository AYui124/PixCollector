"""系统配置项模型."""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class SystemConfig(BaseModel):
    """系统配置项模型（key-value存储）."""

    __tablename__ = 'system_config'

    config_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    config_value: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    value_type: Mapped[str] = mapped_column(
        String(20), default='string', nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        # 根据类型转换值
        value: int | float | bool | datetime | str | None
        if self.value_type == 'integer':
            value = int(self.config_value) if self.config_value else None
        elif self.value_type == 'float':
            value = (
                float(self.config_value)
                if self.config_value else None
            )
        elif self.value_type == 'boolean':
            value = (
                self.config_value == 'true'
                if self.config_value else False
            )
        elif self.value_type == 'datetime':
            value = (
                datetime.strptime(
                    self.config_value, '%Y-%m-%d %H:%M:%S'
                )
                if self.config_value else None
            )
        else:
            value = self.config_value

        return {
            'id': self.id,
            'key': self.config_key,
            'value': value,
            'value_type': self.value_type,
            'description': self.description,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

    def int_value(self) -> int | None:
        try:
            if self.config_value is None:
                return None
            value = int(self.config_value)
            return value
        except (ValueError, TypeError):
            return None
