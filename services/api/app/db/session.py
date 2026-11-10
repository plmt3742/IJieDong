"""Async database engine and session dependency.

Demo v0 runs on SQLite (``sqlite+aiosqlite``). The same factory accepts any
SQLAlchemy async URL so production can switch to PostgreSQL without code changes.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.requests import Request

_SQLITE_PREFIXES = ("sqlite+aiosqlite:///", "sqlite:///")


def _configure_sqlite_connection(engine: AsyncEngine, database_url: str) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if ":memory:" not in database_url:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def ensure_sqlite_parent_directory(database_url: str) -> None:
    """Create the parent directory for file-based SQLite URLs."""
    for prefix in _SQLITE_PREFIXES:
        if not database_url.startswith(prefix):
            continue
        raw_path = database_url[len(prefix) :].split("?", 1)[0]
        if not raw_path or raw_path.startswith(":memory:"):
            return
        Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        return


def create_engine_and_sessionmaker(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build the async engine and session factory for ``database_url``."""
    ensure_sqlite_parent_directory(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_async_engine(database_url, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        _configure_sqlite_connection(engine, database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    return engine, sessionmaker


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session."""
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        raise RuntimeError("Database sessionmaker is not configured on the application")
    async with sessionmaker() as session:
        yield session
