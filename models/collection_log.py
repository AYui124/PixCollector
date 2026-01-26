"""采集日志模型."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class CollectionLog(BaseModel):
    """采集日志模型."""

    __tablename__ = 'collection_logs'

    log_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    artworks_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now,
        nullable=False, index=True
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'id': self.id,
            'log_type': self.log_type,
            'status': self.status,
            'message': self.message,
            'artworks_count': self.artworks_count,
            'created_at': format_datetime(self.created_at)
        }
