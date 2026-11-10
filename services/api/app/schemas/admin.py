"""Administration schemas for applications, users, audit logs, and imports."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import is_strong_password

AssignableRole = Literal["viewer", "editor", "approver", "admin"]
UserStatus = Literal["active", "disabled"]
ImportMode = Literal["atomic", "partial"]


def _validate_optional_password(value: str | None) -> str | None:
    if value is not None and not is_strong_password(value):
        raise ValueError("initial_password must be at least 10 characters with letters and digits")
    return value


class ApplicationOut(BaseModel):
    id: int
    application_no: str
    display_name: str
    unit: str
    phone: str | None = None
    status: str
    resubmit_count: int
    submitted_at: datetime
    reviewed_at: datetime | None = None
    reject_reason: str | None = None


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: AssignableRole = "viewer"
    unit: str | None = Field(None, min_length=2, max_length=50)
    note: str | None = Field(None, max_length=200)
    initial_password: str | None = Field(None, min_length=10, max_length=128)

    @field_validator("initial_password")
    @classmethod
    def password_strength(cls, value: str | None) -> str | None:
        return _validate_optional_password(value)


class ApproveOut(BaseModel):
    application_id: int
    status: str
    user_id: int
    username: str
    role: str
    initial_password: str


class RejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(..., min_length=5, max_length=200)


class UserAdminOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    status: str
    unit: str | None = None
    phone: str | None = None
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: AssignableRole | None = None
    status: UserStatus | None = None
    unit: str | None = Field(None, min_length=2, max_length=50)
    display_name: str | None = Field(None, min_length=2, max_length=20)


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    created_at: datetime


class ImportIssueOut(BaseModel):
    row_number: int | None = None
    column: str | None = None
    code: str
    message: str
    suggestion: str | None = None
    severity: str | None = None
    region_name: str | None = None
    indicator_name: str | None = None


class ImportJobOut(BaseModel):
    id: int
    job_type: str
    filename: str | None = None
    status: str
    mode: str
    total_rows: int
    success_rows: int
    error_rows: int
    source_id: int | None = None
    created_by: int | None = None
    created_at: datetime
    finished_at: datetime | None = None
    errors: list[ImportIssueOut] | None = None


class ImportErrorsOut(BaseModel):
    job_id: int
    errors: list[ImportIssueOut]
