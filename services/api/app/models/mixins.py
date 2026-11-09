"""Shared column helpers for the Demo v0 domain models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column


def bigint_pk_type() -> BigInteger:
    """BIGINT key type that falls back to SQLite's rowid-backed INTEGER.

    SQLite only autoincrements columns declared exactly ``INTEGER PRIMARY KEY``.
    Using the same variant for primary and foreign keys keeps the two sides
    type-compatible on both SQLite and PostgreSQL.
    """
    return BigInteger().with_variant(Integer(), "sqlite")


class TimestampMixin:
    """``created_at`` / ``updated_at`` columns backed by the database clock."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
