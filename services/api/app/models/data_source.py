"""Data source registry model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import bigint_pk_type


class DataSource(Base):
    """Origin of one or more observations (manual entry, Excel import, API)."""

    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('manual', 'excel', 'api', 'demo')",
            name="ck_data_sources_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
