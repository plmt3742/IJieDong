"""Authentication, account application, and session schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import is_strong_password

CHINA_MOBILE_PATTERN = r"^1[3-9]\d{9}$"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str
    unit: str | None = None
    status: str


class LoginData(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(..., min_length=2, max_length=20)
    unit: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., pattern=CHINA_MOBILE_PATTERN)
    reason: str = Field(..., min_length=10, max_length=200)
    privacy_consent: bool

    @field_validator("privacy_consent")
    @classmethod
    def consent_must_be_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("privacy_consent must be true")
        return value


class ApplicationSubmitOut(BaseModel):
    application_no: str
    status: str
    status_token: str
    submitted_at: datetime


class ApplicationStatusOut(BaseModel):
    application_no: str
    status: str
    reject_reason: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError("new_password must be at least 10 characters with letters and digits")
        return value


class ChangePasswordOut(BaseModel):
    status: Literal["ok"] = "ok"
