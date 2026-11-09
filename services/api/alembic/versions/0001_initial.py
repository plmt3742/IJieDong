"""Demo v0 initial schema.

Revision ID: 0001
Revises:
Create Date: 2026-11-10

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _pk_type() -> sa.BigInteger:
    """BIGINT key that autoincrements on SQLite (INTEGER PRIMARY KEY)."""
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    # --- regions (self-referencing tree) -----------------------------------
    op.create_table(
        "regions",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("external_code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column(
            "category",
            sa.String(length=32),
            nullable=False,
            server_default="administrative",
        ),
        sa.Column(
            "parent_id",
            _pk_type(),
            sa.ForeignKey("regions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "level IN ('district', 'town', 'village')",
            name="ck_regions_level",
        ),
        sa.CheckConstraint(
            "category IN ('administrative', 'development_zone')",
            name="ck_regions_category",
        ),
        sa.UniqueConstraint("code", name="uq_regions_code"),
    )
    op.create_index("ix_regions_parent_id", "regions", ["parent_id"])
    op.create_index("ix_regions_level", "regions", ["level"])
    op.create_index("ix_regions_name", "regions", ["name"])

    # --- region_aliases -----------------------------------------------------
    op.create_table(
        "region_aliases",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "region_id",
            _pk_type(),
            sa.ForeignKey("regions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(length=128), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="import",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "region_id",
            "alias",
            name="uq_region_aliases_region_alias",
        ),
    )

    # --- indicators ---------------------------------------------------------
    op.create_table(
        "indicators",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("value_type", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("applicable_levels", sa.JSON(), nullable=False),
        sa.Column("applicable_region_categories", sa.JSON(), nullable=True),
        sa.Column(
            "aggregation",
            sa.String(length=16),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "precision",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("max_length", sa.Integer(), nullable=True),
        sa.Column(
            "direction",
            sa.String(length=16),
            nullable=False,
            server_default="neutral",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_indicators_code"),
    )

    # --- data_sources -------------------------------------------------------
    op.create_table(
        "data_sources",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'excel', 'api', 'demo')",
            name="ck_data_sources_source_type",
        ),
    )

    # --- users --------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("unit", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("wechat_openid", sa.String(length=64), nullable=True),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'editor', 'viewer', 'approver')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_users_status",
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("wechat_openid", name="uq_users_wechat_openid"),
    )

    # --- import_jobs --------------------------------------------------------
    op.create_table(
        "import_jobs",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "mode",
            sa.String(length=16),
            nullable=False,
            server_default="atomic",
        ),
        sa.Column(
            "total_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "success_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_report_path", sa.String(length=255), nullable=True),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column(
            "created_by",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "job_type IN ('excel', 'api', 'manual')",
            name="ck_import_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'success', 'partial', 'failed')",
            name="ck_import_jobs_status",
        ),
        sa.CheckConstraint(
            "mode IN ('atomic', 'partial')",
            name="ck_import_jobs_mode",
        ),
        sa.CheckConstraint("total_rows >= 0", name="ck_import_jobs_total_rows"),
        sa.CheckConstraint("success_rows >= 0", name="ck_import_jobs_success_rows"),
        sa.CheckConstraint("error_rows >= 0", name="ck_import_jobs_error_rows"),
    )

    # --- data_values (contract name: observations) --------------------------
    op.create_table(
        "data_values",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "region_id",
            _pk_type(),
            sa.ForeignKey("regions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "indicator_id",
            _pk_type(),
            sa.ForeignKey("indicators.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "period_type",
            sa.String(length=16),
            nullable=False,
            server_default="year",
        ),
        sa.Column("value_number", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column(
            "quality_status",
            sa.String(length=16),
            nullable=False,
            server_default="verified",
        ),
        sa.Column(
            "source_id",
            _pk_type(),
            sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "import_job_id",
            _pk_type(),
            sa.ForeignKey("import_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dimensions", sa.JSON(), nullable=True),
        sa.Column(
            "dimension_hash",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="published",
        ),
        sa.Column(
            "updated_by",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "quality_status IN "
            "('missing', 'not_applicable', 'suppressed', 'estimated', "
            "'provisional', 'verified')",
            name="ck_data_values_quality_status",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_data_values_status",
        ),
        sa.UniqueConstraint(
            "region_id",
            "indicator_id",
            "period_year",
            "period_type",
            "dimension_hash",
            name="uq_data_values_region_indicator_period_dimension",
        ),
    )
    op.create_index(
        "ix_data_values_indicator_period",
        "data_values",
        ["indicator_id", "period_year"],
    )
    op.create_index(
        "ix_data_values_region_period",
        "data_values",
        ["region_id", "period_year"],
    )
    op.create_index(
        "ix_data_values_indicator_period_value",
        "data_values",
        ["indicator_id", "period_year", "value_number"],
    )
    op.create_index(
        "ix_data_values_import_job_id",
        "data_values",
        ["import_job_id"],
    )

    # --- user_applications --------------------------------------------------
    op.create_table(
        "user_applications",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column("application_no", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("status_token_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "reviewed_by",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column(
            "resubmit_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_user_applications_status",
        ),
        sa.UniqueConstraint(
            "application_no",
            name="uq_user_applications_application_no",
        ),
    )
    op.create_index(
        "ix_user_applications_phone_status",
        "user_applications",
        ["phone", "status"],
    )
    op.create_index(
        "ix_user_applications_status_created_at",
        "user_applications",
        ["status", "created_at"],
    )

    # --- chat_sessions ------------------------------------------------------
    op.create_table(
        "chat_sessions",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- chat_messages ------------------------------------------------------
    op.create_table(
        "chat_messages",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            _pk_type(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("chart_spec", sa.JSON(), nullable=True),
        sa.Column("blocks", sa.JSON(), nullable=True),
        sa.Column("data_snapshot", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'tool')",
            name="ck_chat_messages_role",
        ),
    )
    op.create_index(
        "ix_chat_messages_session_created_at",
        "chat_messages",
        ["session_id", "created_at"],
    )

    # --- export_jobs --------------------------------------------------------
    op.create_table(
        "export_jobs",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=80), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('answer', 'view', 'query')",
            name="ck_export_jobs_source_type",
        ),
        sa.CheckConstraint(
            "format IN ('png', 'pdf', 'xlsx', 'csv', 'json')",
            name="ck_export_jobs_format",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'ready', 'failed', 'expired')",
            name="ck_export_jobs_status",
        ),
    )
    op.create_index(
        "ix_export_jobs_user_created_at",
        "export_jobs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_export_jobs_status_created_at",
        "export_jobs",
        ["status", "created_at"],
    )
    op.create_index("ix_export_jobs_expires_at", "export_jobs", ["expires_at"])
    op.create_index(
        "ix_export_jobs_source",
        "export_jobs",
        ["source_type", "source_id"],
    )

    # --- audit_logs ---------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", _pk_type(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            _pk_type(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_audit_logs_user_created_at",
        "audit_logs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    # Reverse dependency order: dependants before the tables they reference.
    op.drop_table("audit_logs")
    op.drop_table("export_jobs")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("user_applications")
    op.drop_table("data_values")
    op.drop_table("import_jobs")
    op.drop_table("users")
    op.drop_table("data_sources")
    op.drop_table("indicators")
    op.drop_table("region_aliases")
    op.drop_table("regions")
