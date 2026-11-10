"""Export job model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import bigint_pk_type


class ExportJob(Base):
    """One rendered export artifact and its lifecycle metadata."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('answer', 'view', 'query', 'report')",
            name="ck_export_jobs_source_type",
        ),
        CheckConstraint(
            "format IN ('png', 'pdf', 'xlsx', 'csv', 'json')",
            name="ck_export_jobs_format",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'ready', 'failed', 'expired')",
            name="ck_export_jobs_status",
        ),
        Index("ix_export_jobs_user_created_at", "user_id", "created_at"),
        Index("ix_export_jobs_status_created_at", "status", "created_at"),
        Index("ix_export_jobs_expires_at", "expires_at"),
        Index("ix_export_jobs_source", "source_type", "source_id"),
        Index("uq_export_jobs_export_id", "export_id", unique=True),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    export_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_id: Mapped[int] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="queued",
        server_default="queued",
    )
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target: Mapped[str | None] = mapped_column(String(32), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    view_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer_blocks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    component_versions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    registry_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    renderer_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
