"""Authentication, account application, and import source columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table)}


def _unique_constraints(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for constraint in inspector.get_unique_constraints(table):
        name = constraint.get("name")
        if name:
            names.add(name)
    return names


def _foreign_keys(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for constraint in inspector.get_foreign_keys(table):
        name = constraint.get("name")
        if name:
            names.add(name)
    return names


def upgrade() -> None:
    user_columns = _columns("users")
    user_uniques = _unique_constraints("users")
    with op.batch_alter_table("users") as batch:
        if "token_version" not in user_columns:
            batch.add_column(
                sa.Column(
                    "token_version",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )
        if "uq_users_phone" not in user_uniques:
            batch.create_unique_constraint("uq_users_phone", ["phone"])

    application_columns = _columns("user_applications")
    application_fks = _foreign_keys("user_applications")
    with op.batch_alter_table("user_applications") as batch:
        if "privacy_consent" not in application_columns:
            batch.add_column(
                sa.Column(
                    "privacy_consent",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if "privacy_notice_version" not in application_columns:
            batch.add_column(
                sa.Column("privacy_notice_version", sa.String(length=32), nullable=True)
            )
        if "created_user_id" not in application_columns:
            batch.add_column(
                sa.Column(
                    "created_user_id",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                    nullable=True,
                )
            )
        if "submitted_ip" not in application_columns:
            batch.add_column(sa.Column("submitted_ip", sa.String(length=45), nullable=True))
        if "submitted_user_agent" not in application_columns:
            batch.add_column(
                sa.Column("submitted_user_agent", sa.String(length=512), nullable=True)
            )
        if "fk_user_applications_created_user_id" not in application_fks:
            batch.create_foreign_key(
                "fk_user_applications_created_user_id",
                "users",
                ["created_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

    import_columns = _columns("import_jobs")
    import_fks = _foreign_keys("import_jobs")
    with op.batch_alter_table("import_jobs") as batch:
        if "source_id" not in import_columns:
            batch.add_column(
                sa.Column(
                    "source_id",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                    nullable=True,
                )
            )
        if "fk_import_jobs_source_id" not in import_fks:
            batch.create_foreign_key(
                "fk_import_jobs_source_id",
                "data_sources",
                ["source_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    import_columns = _columns("import_jobs")
    import_fks = _foreign_keys("import_jobs")
    with op.batch_alter_table("import_jobs") as batch:
        if "fk_import_jobs_source_id" in import_fks:
            batch.drop_constraint("fk_import_jobs_source_id", type_="foreignkey")
        if "source_id" in import_columns:
            batch.drop_column("source_id")

    application_columns = _columns("user_applications")
    application_fks = _foreign_keys("user_applications")
    with op.batch_alter_table("user_applications") as batch:
        if "fk_user_applications_created_user_id" in application_fks:
            batch.drop_constraint("fk_user_applications_created_user_id", type_="foreignkey")
        for column in (
            "submitted_user_agent",
            "submitted_ip",
            "created_user_id",
            "privacy_notice_version",
            "privacy_consent",
        ):
            if column in application_columns:
                batch.drop_column(column)

    user_columns = _columns("users")
    user_uniques = _unique_constraints("users")
    with op.batch_alter_table("users") as batch:
        if "uq_users_phone" in user_uniques:
            batch.drop_constraint("uq_users_phone", type_="unique")
        if "token_version" in user_columns:
            batch.drop_column("token_version")
