"""Tests for the Demo v0 SQLAlchemy domain model metadata."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.models import (
    AuditLog,
    ChatMessage,
    ChatSession,
    DataSource,
    DataValue,
    ExportJob,
    ImportJob,
    Indicator,
    Region,
    RegionAlias,
    User,
    UserApplication,
)

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

EXPECTED_CLASSES = {
    AuditLog,
    ChatMessage,
    ChatSession,
    DataSource,
    DataValue,
    ExportJob,
    ImportJob,
    Indicator,
    Region,
    RegionAlias,
    User,
    UserApplication,
}


def test_all_demo_v0_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert {model.__table__.name for model in EXPECTED_CLASSES} == EXPECTED_TABLES


def test_models_use_sqlite_friendly_bigint_keys() -> None:
    sqlite_dialect = sqlite.dialect()
    postgres_dialect = postgresql.dialect()

    for table in Base.metadata.tables.values():
        id_column = table.c["id"]
        assert id_column.primary_key
        assert id_column.type.compile(dialect=sqlite_dialect) == "INTEGER"
        assert id_column.type.compile(dialect=postgres_dialect) == "BIGINT"


def test_data_values_unique_key_and_indexes() -> None:
    table = Base.metadata.tables["data_values"]

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert (
        "region_id",
        "indicator_id",
        "period_year",
        "period_type",
        "dimension_hash",
    ) in unique_columns

    indexes = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
        if isinstance(index, Index) and index.name is not None
    }
    assert indexes.get("ix_data_values_indicator_period") == (
        "indicator_id",
        "period_year",
    )
    assert indexes.get("ix_data_values_region_period") == (
        "region_id",
        "period_year",
    )
    assert indexes.get("ix_data_values_indicator_period_value") == (
        "indicator_id",
        "period_year",
        "value_number",
    )
    assert indexes.get("ix_data_values_import_job_id") == ("import_job_id",)


def test_users_role_and_status_checks_are_named() -> None:
    table = Base.metadata.tables["users"]
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_users_role" in checks
    assert "ck_users_status" in checks
    assert "admin" in checks["ck_users_role"]
    assert "approver" in checks["ck_users_role"]
    assert "active" in checks["ck_users_status"]
    assert "disabled" in checks["ck_users_status"]


def test_all_relationship_mappers_configure() -> None:
    configure_mappers()
