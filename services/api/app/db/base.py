"""SQLAlchemy 2.0 declarative base.

Domain models and migrations are owned by B01; this module intentionally defines
no tables.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all future ORM models."""
