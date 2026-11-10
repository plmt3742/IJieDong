"""Mini-program account application model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class UserApplication(TimestampMixin, Base):
    """Access request submitted from the mini-program before a user exists."""

    __tablename__ = "user_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_user_applications_status",
        ),
        UniqueConstraint(
            "application_no",
            name="uq_user_applications_application_no",
        ),
        Index(
            "ix_user_applications_phone_status",
            "phone",
            "status",
        ),
        Index(
            "ix_user_applications_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    application_no: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    status_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resubmit_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    privacy_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    privacy_notice_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_user_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    submitted_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
