"""User account model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class User(TimestampMixin, Base):
    """Back-office or mini-program account (guests/applicants are not users)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'editor', 'viewer', 'approver')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_users_status",
        ),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("wechat_openid", name="uq_users_wechat_openid"),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
    )
    unit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wechat_openid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    token_version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
