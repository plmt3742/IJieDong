"""Fixtures for query API tests.

The fixture mirrors the B02 seed test pattern: migrate a temporary SQLite file,
run the deterministic seed once, then point a real application instance at the
same file. No pytest-asyncio plugin is required.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from scripts.seed_demo import seed_demo

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = API_ROOT / "alembic.ini"
ALEMBIC_SCRIPTS = API_ROOT / "alembic"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture()
def seeded_client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient backed by a migrated and deterministically seeded SQLite file."""
    database_path = tmp_path / "query_api.db"
    sync_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(_alembic_config(sync_url), "head")
    asyncio.run(seed_demo(sync_url))

    app = create_app(
        settings=Settings(
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            llm_provider=None,
            llm_api_key=None,
            llm_base_url=None,
            llm_model=None,
        )
    )
    with TestClient(app) as client:
        yield client
