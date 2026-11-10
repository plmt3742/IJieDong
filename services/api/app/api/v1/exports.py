"""Export creation, status, and download endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.core.security import TokenError, bearer_scheme, decode_access_token
from app.db.session import get_db
from app.models import User
from app.schemas.common import ItemEnvelope, Meta
from app.services import export_service
from app.services.export_service import (
    ALLOWED_ROLES,
    ExportCreateRequest,
    ExportJobOut,
)

router = APIRouter(prefix="/exports", tags=["exports"])


async def get_export_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError(
            "EXPORT_FORBIDDEN",
            "Guests cannot export; sign in with an approved account",
            status_code=403,
        )
    settings: Settings = request.app.state.settings
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except TokenError as exc:
        raise AppError(
            "AUTH_INVALID",
            "Authentication token is invalid or expired",
            status_code=401,
        ) from exc
    user = await session.get(User, payload.user_id)
    if user is None:
        raise AppError(
            "AUTH_INVALID",
            "Authentication token is invalid or expired",
            status_code=401,
        )
    if user.status != "active":
        raise AppError("USER_DISABLED", "User account is disabled", status_code=403)
    if user.token_version != payload.token_version:
        raise AppError(
            "AUTH_INVALID",
            "Authentication token is invalid or expired",
            status_code=401,
        )
    if user.role not in ALLOWED_ROLES:
        raise AppError(
            "EXPORT_FORBIDDEN",
            "Current role cannot export",
            status_code=403,
        )
    return user


@router.post(
    "",
    response_model=ItemEnvelope[ExportJobOut],
    status_code=201,
    summary="Create an export synchronously",
    description=(
        "The user must choose a format explicitly; there is no default. Guests "
        "and unapproved applicants receive 403 EXPORT_FORBIDDEN."
    ),
)
async def create_export_endpoint(
    request: Request,
    body: ExportCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_export_user)],
) -> ItemEnvelope[ExportJobOut]:
    settings: Settings = request.app.state.settings
    job = await export_service.create_export(
        session,
        request=request,
        settings=settings,
        user=user,
        payload=body,
    )
    return ItemEnvelope(data=job, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/{export_id}",
    response_model=ItemEnvelope[ExportJobOut],
    summary="Get export status",
)
async def get_export_endpoint(
    request: Request,
    export_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_export_user)],
) -> ItemEnvelope[ExportJobOut]:
    job = await export_service.get_export(session, export_id=export_id, user=user)
    return ItemEnvelope(data=job, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/{export_id}/download",
    summary="Download an export file",
    responses={410: {"description": "Export expired"}, 403: {"description": "Not the owner"}},
)
async def download_export_endpoint(
    request: Request,
    export_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_export_user)],
) -> FileResponse:
    settings: Settings = request.app.state.settings
    path, filename, media_type = await export_service.download_export(
        session,
        request=request,
        export_id=export_id,
        user=user,
        settings=settings,
    )
    return FileResponse(path=path, media_type=media_type, filename=filename)
