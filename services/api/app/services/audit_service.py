"""Audit log helper shared by the auth, admin, and import services."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.models import AuditLog


def _request_metadata(request: Request | None) -> tuple[str | None, str | None, str | None]:
    if request is None:
        return None, None, None
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if user_agent is not None:
        user_agent = user_agent[:512]
    return ip, user_agent, get_request_id(request)


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
    user_id: int | None = None,
) -> AuditLog:
    ip, user_agent, request_id = _request_metadata(request)
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=detail,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
    )
    session.add(entry)
    await session.flush()
    return entry
