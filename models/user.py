"""用户模型."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from core.database import BaseModel
from utils.time_utils import format_datetime, get_utc_now


class User(BaseModel):
    """用户模型，用于Web认证."""

    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(
        String(50), unique=True,
        nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now,
        nullable=False
    )

    def set_password(self, password: str) -> None:
        """设置密码哈希."""
        self.password_hash = generate_password_hash(password)

    def check_password(
        self, password: str
    ) -> bool:
        """验证密码."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'created_at': format_datetime(self.created_at)
        }
