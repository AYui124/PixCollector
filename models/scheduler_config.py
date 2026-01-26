"""定时任务配置模型."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class SchedulerConfig(BaseModel):
    """定时任务配置模型."""

    __tablename__ = 'scheduler_configs'

    collect_type: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    crontab_expression: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_run_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
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
        return {
            'id': self.id,
            'collect_type': self.collect_type,
            'crontab_expression': self.crontab_expression,
            'is_active': self.is_active,
            'last_run_time': format_datetime(self.last_run_time),
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }
