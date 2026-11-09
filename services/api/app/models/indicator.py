"""Indicator registry model."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class Indicator(TimestampMixin, Base):
    """Metadata describing one measurable/registered indicator.

    ``value_type`` and ``unit`` intentionally carry no CHECK constraint: the
    target model adds date/boolean/json/geo types and custom units in M1.
    """

    __tablename__ = "indicators"
    __table_args__ = (UniqueConstraint("code", name="uq_indicators_code"),)

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    applicable_levels: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    applicable_region_categories: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    aggregation: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="none",
        server_default="none",
    )
    precision: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="neutral",
        server_default="neutral",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
    )
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
