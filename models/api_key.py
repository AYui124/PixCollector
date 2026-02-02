"""API密钥模型."""
from datetime import datetime
from secrets import token_hex

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class ApiKey(BaseModel):
    """API密钥模型."""

    __tablename__ = 'api_keys'

    key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    @staticmethod
    def generate_key() -> str:
        """
        生成随机API密钥.

        Returns:
            32字符的十六进制字符串
        """
        return token_hex(16)

    def to_dict(self) -> dict:
        """
        转换为字典.

        Returns:
            字典表示
        """
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': format_datetime(self.created_at),
            'last_used_at': (
                format_datetime(self.last_used_at)
                if self.last_used_at else None
            ),
            'usage_count': self.usage_count
        }

    def update_usage(self) -> None:
        """更新使用统计."""
        self.last_used_at = get_utc_now()
        self.usage_count += 1
