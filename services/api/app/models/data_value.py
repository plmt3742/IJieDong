"""Observation model (contract name ``observations``, physical table ``data_values``)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class DataValue(TimestampMixin, Base):
    """One value for a region/indicator/period/dimension combination.

    NULL value columns mean "no data"; zero is a real measurement. ``status``
    gates publication while ``quality_status`` records provenance/completeness.
    """

    __tablename__ = "data_values"
    __table_args__ = (
        CheckConstraint(
            "quality_status IN "
            "('missing', 'not_applicable', 'suppressed', 'estimated', "
            "'provisional', 'verified')",
            name="ck_data_values_quality_status",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_data_values_status",
        ),
        UniqueConstraint(
            "region_id",
            "indicator_id",
            "period_year",
            "period_type",
            "dimension_hash",
            name="uq_data_values_region_indicator_period_dimension",
        ),
        Index(
            "ix_data_values_indicator_period",
            "indicator_id",
            "period_year",
        ),
        Index(
            "ix_data_values_region_period",
            "region_id",
            "period_year",
        ),
        Index(
            "ix_data_values_indicator_period_value",
            "indicator_id",
            "period_year",
            "value_number",
        ),
        Index("ix_data_values_import_job_id", "import_job_id"),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    region_id: Mapped[int] = mapped_column(
        bigint_pk_type(),
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
    )
    indicator_id: Mapped[int] = mapped_column(
        bigint_pk_type(),
        ForeignKey("indicators.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="year",
        server_default="year",
    )
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    quality_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="verified",
        server_default="verified",
    )
    source_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    import_job_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dimension_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        server_default="",
    )
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="published",
        server_default="published",
    )
    updated_by: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
