"""数据库模型定义 - SQLAlchemy 2.0 Typed ORM."""
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    """声明式基类."""
    pass


# 创建SQLAlchemy实例
db = SQLAlchemy()


class User(Base):
    """用户模型，用于Web认证."""

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def set_password(self, password: str) -> None:
        """设置密码哈希."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证密码."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Artwork(Base):
    """作品模型."""

    __tablename__ = 'artworks'
    __table_args__ = (
        UniqueConstraint('illust_id', 'page_index', name='uq_illust_page'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    illust_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    share_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    total_bookmarks: Mapped[int] = mapped_column(Integer, default=0)
    total_view: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_r18: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    collect_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            'ranking_works, follow_new_works, '
            'follow_user_artworks, follow_new_follow, '
            'update_artworks'
        )
    )
    type: Mapped[str] = mapped_column(
        String(20),
        default='illust',
        nullable=False,
        index=True,
        comment='作品类型: illust, manga, ugoira'
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    post_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment='作品创作时间'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False, index=True
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        rank_date_str = None
        if self.rank_date:
            rank_date_str = self.rank_date.strftime('%Y-%m-%d')

        last_updated_str = None
        if self.last_updated_at:
            last_updated_str = self.last_updated_at.strftime(
                '%Y-%m-%d %H:%M:%S'
            )

        # 将UTC时间转换为本地时间
        post_date_local = (
            self.post_date.replace(tzinfo=UTC)
            .astimezone()
        )

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
            'rank_date': rank_date_str,
            'tags': self.tags,
            'is_r18': self.is_r18,
            'type': self.type,
            'collect_type': self.collect_type,
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'last_updated_at': last_updated_str,
            'post_date': post_date_local.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Follow(Base):
    """关注用户模型."""

    __tablename__ = 'follows'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 采集时间跟踪
    first_collect_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        comment='首次关注该用户的日期'
    )
    last_collect_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        comment='上次采集该用户作品的日期'
    )

    # 最后发布作品时间
    last_artwork_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        comment='该用户最后发布作品的时间'
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        first_collect_str = None
        if self.first_collect_date:
            first_collect_str = self.first_collect_date.strftime('%Y-%m-%d')

        last_collect_str = None
        if self.last_collect_date:
            last_collect_str = self.last_collect_date.strftime(
                '%Y-%m-%d %H:%M:%S'
            )

        last_artwork_str = None
        if self.last_artwork_date:
            last_artwork_str = self.last_artwork_date.strftime(
                '%Y-%m-%d %H:%M:%S'
            )

        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'avatar_url': self.avatar_url,
            'first_collect_date': first_collect_str,
            'last_collect_date': last_collect_str,
            'last_artwork_date': last_artwork_str,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class CollectionLog(Base):
    """采集日志模型."""

    __tablename__ = 'collection_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            'daily_rank,'
            'follow_new_follow,'
            'follow_new_works,'
            'update_artworks'
        )
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment='success, failed'
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    artworks_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
        index=True
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'id': self.id,
            'type': self.log_type,
            'status': self.status,
            'message': self.message,
            'artworks_count': self.artworks_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class SchedulerConfig(Base):
    """定时任务配置模型."""

    __tablename__ = 'scheduler_configs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collect_type: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    crontab_expression: Mapped[str] = mapped_column(
        String(100), default='0 0 * * * *', nullable=False,
        comment='Cron表达式: 秒 分 时 日 月 周'
    )
    last_run_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        comment='任务最后执行时间'
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        last_run_str = None
        if self.last_run_time:
            last_run_str = self.last_run_time.strftime('%Y-%m-%d %H:%M:%S')

        return {
            'id': self.id,
            'collect_type': self.collect_type,
            'crontab_expression': self.crontab_expression,
            'last_run_time': last_run_str,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class SystemConfig(Base):
    """系统配置项模型（key-value存储）."""

    __tablename__ = 'system_config'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    config_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(
        String(20),
        default='string',
        nullable=False,
        comment='string, integer, float, boolean, datetime'
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        # 根据类型转换值
        value: int | float | bool | datetime | str | None
        if self.value_type == 'integer':
            value = int(self.config_value) if self.config_value else None
        elif self.value_type == 'float':
            value = float(self.config_value) if self.config_value else None
        elif self.value_type == 'boolean':
            value = self.config_value == 'true' if self.config_value else False
        elif self.value_type == 'datetime':
            value = (
                datetime.strptime(self.config_value, '%Y-%m-%d %H:%M:%S')
                if self.config_value
                else None
            )
        else:
            value = self.config_value

        return {
            'id': self.id,
            'key': self.config_key,
            'value': value,
            'value_type': self.value_type,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def int_value(self) -> int | None:
        try:
            if self.config_value is None:
                return None
            value = int(self.config_value)
            return value
        except (ValueError, TypeError):
            return None
