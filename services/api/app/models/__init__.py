"""SQLAlchemy models for the Demo v0 schema.

Importing this package registers every table on ``app.db.base.Base.metadata``;
Alembic's environment imports it so autogenerate/migrations see the full schema.
"""
from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.chat import ChatMessage, ChatSession
from app.models.data_source import DataSource
from app.models.data_value import DataValue
from app.models.export_job import ExportJob
from app.models.import_job import ImportJob
from app.models.indicator import Indicator
from app.models.region import Region, RegionAlias
from app.models.user import User
from app.models.user_application import UserApplication

__all__ = [
    "AuditLog",
    "ChatMessage",
    "ChatSession",
    "DataSource",
    "DataValue",
    "ExportJob",
    "ImportJob",
    "Indicator",
    "Region",
    "RegionAlias",
    "User",
    "UserApplication",
]
