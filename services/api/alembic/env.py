"""Alembic environment for the i揭东 API service.

The application runs on an async driver (``sqlite+aiosqlite`` in Demo v0,
``postgresql+asyncpg`` in production). Alembic itself is synchronous, so this
module derives a sync URL either from ``sqlalchemy.url`` (tests/CI) or from the
application settings (CLI usage).
"""
from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Make ``app`` importable regardless of the caller's working directory.
_API_ROOT = Path(__file__).resolve().parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

import app.models  # noqa: E402,F401  (registers all tables on Base.metadata)
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata


def to_sync_url(database_url: str) -> str:
    """Strip the async driver suffix from a SQLAlchemy URL.

    ``sqlite+aiosqlite:///...`` -> ``sqlite:///...``
    ``postgresql+asyncpg://...`` -> ``postgresql://...``
    """
    scheme, separator, remainder = database_url.partition("://")
    if not separator:
        return database_url
    if "+" in scheme:
        scheme = scheme.split("+", 1)[0]
    return f"{scheme}://{remainder}"


def resolve_database_url() -> str:
    """Return the synchronous database URL for this migration run."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return to_sync_url(configured)
    return to_sync_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Emit SQL without connecting (``alembic upgrade --sql``)."""
    context.configure(
        url=resolve_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live synchronous connection."""
    connectable = create_engine(resolve_database_url(), poolclass=pool.NullPool)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
