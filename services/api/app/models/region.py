"""Region tree and import alias models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class Region(TimestampMixin, Base):
    """Administrative or development-zone node in the three-level tree."""

    __tablename__ = "regions"
    __table_args__ = (
        CheckConstraint(
            "level IN ('district', 'town', 'village')",
            name="ck_regions_level",
        ),
        CheckConstraint(
            "category IN ('administrative', 'development_zone')",
            name="ck_regions_category",
        ),
        UniqueConstraint("code", name="uq_regions_code"),
        Index("ix_regions_parent_id", "parent_id"),
        Index("ix_regions_level", "level"),
        Index("ix_regions_name", "name"),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="administrative",
        server_default="administrative",
    )
    parent_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    parent: Mapped[Region | None] = relationship(
        back_populates="children",
        remote_side=[id],
    )
    children: Mapped[list[Region]] = relationship(back_populates="parent")
    aliases: Mapped[list[RegionAlias]] = relationship(
        back_populates="region",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RegionAlias(Base):
    """Alternative name used when resolving imported region names."""

    __tablename__ = "region_aliases"
    __table_args__ = (
        UniqueConstraint("region_id", "alias", name="uq_region_aliases_region_alias"),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    region_id: Mapped[int] = mapped_column(
        bigint_pk_type(),
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="import",
        server_default="import",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    region: Mapped[Region] = relationship(back_populates="aliases")
