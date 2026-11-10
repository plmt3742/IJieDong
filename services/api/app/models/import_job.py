"""Import batch model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import bigint_pk_type


class ImportJob(Base):
    """One Excel/API/manual import batch with row-level counters."""

    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('excel', 'api', 'manual')",
            name="ck_import_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'partial', 'failed')",
            name="ck_import_jobs_status",
        ),
        CheckConstraint(
            "mode IN ('atomic', 'partial')",
            name="ck_import_jobs_mode",
        ),
        CheckConstraint("total_rows >= 0", name="ck_import_jobs_total_rows"),
        CheckConstraint("success_rows >= 0", name="ck_import_jobs_success_rows"),
        CheckConstraint("error_rows >= 0", name="ck_import_jobs_error_rows"),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(16), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="atomic",
        server_default="atomic",
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    success_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_report_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    errors: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
