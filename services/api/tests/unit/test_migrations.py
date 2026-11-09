"""Tests for the Alembic initial migration (sync SQLite, no pytest-asyncio)."""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = API_ROOT / "alembic.ini"
ALEMBIC_SCRIPTS = API_ROOT / "alembic"

EXPECTED_TABLES = {
    "audit_logs",
    "chat_messages",
    "chat_sessions",
    "data_sources",
    "data_values",
    "export_jobs",
    "import_jobs",
    "indicators",
    "region_aliases",
    "regions",
    "user_applications",
    "users",
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_upgrade_creates_all_tables_and_downgrade_removes_them(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = _alembic_config(database_url)
    engine = create_engine(database_url)

    try:
        command.upgrade(config, "head")

        upgraded_tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES <= upgraded_tables
        assert "alembic_version" in upgraded_tables

        data_value_indexes = {
            index["name"]
            for index in inspect(engine).get_indexes("data_values")
        }
        assert "ix_data_values_indicator_period" in data_value_indexes
        assert "ix_data_values_region_period" in data_value_indexes

        command.downgrade(config, "base")

        remaining_tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.isdisjoint(remaining_tables)
        assert "alembic_version" in remaining_tables
    finally:
        engine.dispose()


def test_upgrade_is_repeatable_from_empty_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'repeat.db').as_posix()}"
    config = _alembic_config(database_url)
    engine = create_engine(database_url)

    try:
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
