"""关注用户模型."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_date, format_datetime, get_utc_now


class Follow(BaseModel):
    """关注用户模型."""

    __tablename__ = 'follows'

    user_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    user_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    first_collect_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_collect_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_artwork_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
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
            'user_id': self.user_id,
            'user_name': self.user_name,
            'avatar_url': self.avatar_url,
            'first_collect_date': format_date(self.first_collect_date),
            'last_collect_date': format_datetime(self.last_collect_date),
            'last_artwork_date': format_datetime(self.last_artwork_date),
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }
