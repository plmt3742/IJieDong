"""AI answer ids and export snapshot columns.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-10

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXPORT_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("export_id", sa.Column("export_id", sa.String(length=32), nullable=True)),
    ("title", sa.Column("title", sa.String(length=120), nullable=True)),
    ("target", sa.Column("target", sa.String(length=32), nullable=True)),
    ("view_spec", sa.Column("view_spec", sa.JSON(), nullable=True)),
    ("answer_blocks", sa.Column("answer_blocks", sa.JSON(), nullable=True)),
    ("component_versions", sa.Column("component_versions", sa.JSON(), nullable=True)),
    ("registry_version", sa.Column("registry_version", sa.String(length=16), nullable=True)),
    ("data_version", sa.Column("data_version", sa.String(length=32), nullable=True)),
    ("data_hash", sa.Column("data_hash", sa.String(length=80), nullable=True)),
    ("renderer_version", sa.Column("renderer_version", sa.String(length=16), nullable=True)),
    ("error_message", sa.Column("error_message", sa.Text(), nullable=True)),
    (
        "download_count",
        sa.Column(
            "download_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    ),
)


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for index in inspector.get_indexes(table):
        name = index.get("name")
        if name:
            names.add(name)
    return names


def _checks(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for constraint in inspector.get_check_constraints(table):
        name = constraint.get("name")
        if name:
            names.add(name)
    return names


def upgrade() -> None:
    export_columns = _columns("export_jobs")
    export_checks = _checks("export_jobs")
    with op.batch_alter_table("export_jobs") as batch:
        for name, column in EXPORT_COLUMNS:
            if name not in export_columns:
                batch.add_column(column)
        if "ck_export_jobs_source_type" in export_checks:
            batch.drop_constraint("ck_export_jobs_source_type", type_="check")
            batch.create_check_constraint(
                "ck_export_jobs_source_type",
                "source_type IN ('answer', 'view', 'query', 'report')",
            )
    if "uq_export_jobs_export_id" not in _indexes("export_jobs"):
        op.create_index(
            "uq_export_jobs_export_id",
            "export_jobs",
            ["export_id"],
            unique=True,
        )

    chat_columns = _columns("chat_messages")
    if "answer_id" not in chat_columns:
        with op.batch_alter_table("chat_messages") as batch:
            batch.add_column(sa.Column("answer_id", sa.String(length=32), nullable=True))
    if "uq_chat_messages_answer_id" not in _indexes("chat_messages"):
        op.create_index(
            "uq_chat_messages_answer_id",
            "chat_messages",
            ["answer_id"],
            unique=True,
        )


def downgrade() -> None:
    if "uq_chat_messages_answer_id" in _indexes("chat_messages"):
        op.drop_index("uq_chat_messages_answer_id", table_name="chat_messages")
    chat_columns = _columns("chat_messages")
    if "answer_id" in chat_columns:
        with op.batch_alter_table("chat_messages") as batch:
            batch.drop_column("answer_id")

    if "uq_export_jobs_export_id" in _indexes("export_jobs"):
        op.drop_index("uq_export_jobs_export_id", table_name="export_jobs")
    export_columns = _columns("export_jobs")
    export_checks = _checks("export_jobs")
    with op.batch_alter_table("export_jobs") as batch:
        if "ck_export_jobs_source_type" in export_checks:
            batch.drop_constraint("ck_export_jobs_source_type", type_="check")
            batch.create_check_constraint(
                "ck_export_jobs_source_type",
                "source_type IN ('answer', 'view', 'query')",
            )
        for name, _ in reversed(EXPORT_COLUMNS):
            if name in export_columns:
                batch.drop_column(name)
