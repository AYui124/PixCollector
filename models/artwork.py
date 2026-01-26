"""作品模型."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class Artwork(BaseModel):
    """作品模型."""

    __tablename__ = 'artworks'

    # 索引
    __table_args__ = (
        Index('idx_post_date', 'post_date'),
    )
    illust_id: Mapped[int] = mapped_column(
        Integer, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_id: Mapped[int] = mapped_column(
        Integer, index=True, nullable=False
    )
    author_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    share_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    page_index: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    page_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    total_bookmarks: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_view: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    tags: Mapped[str] = mapped_column(Text, default='', nullable=False)
    is_r18: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    collect_type: Mapped[str] = mapped_column(
        String(50), default='', nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(20), default='illust',
        nullable=False, index=True
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    post_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now,
        nullable=False
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'id': self.id,
            'illust_id': self.illust_id,
            'title': self.title,
            'author_id': self.author_id,
            'author_name': self.author_name,
            'url': self.url,
            'share_url': self.share_url,
            'page_index': self.page_index,
            'page_count': self.page_count,
            'total_bookmarks': self.total_bookmarks,
            'total_view': self.total_view,
            'rank': self.rank,
            'rank_date': format_datetime(self.rank_date, '%Y-%m-%d'),
            'tags': self.tags.split(',') if self.tags else [],
            'is_r18': self.is_r18,
            'type': self.type,
            'collect_type': self.collect_type,
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'last_updated_at': format_datetime(self.last_updated_at),
            'post_date': format_datetime(self.post_date),
            'created_at': format_datetime(self.created_at)
        }
