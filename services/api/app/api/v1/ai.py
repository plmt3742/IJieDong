"""AI chat and session endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rate_limit import enforce_ai_rate_limit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.core.security import (
    TokenError,
    bearer_scheme,
    decode_access_token,
    get_current_user,
)
from app.db.session import get_db
from app.models import User
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    ChatMessageOut,
    ChatSessionOut,
)
from app.schemas.common import ItemEnvelope, ListEnvelope, Meta
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
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
    return user


@router.post(
    "/chat",
    response_model=ItemEnvelope[AIChatResponse],
    summary="Ask a data question",
    description=(
        "Guests may ask up to the daily quota; authenticated users keep history. "
        "Answers use read-only tools and always carry citations or an explicit "
        "no-data/refused notice."
    ),
)
async def chat_endpoint(
    request: Request,
    body: AIChatRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
) -> ItemEnvelope[AIChatResponse]:
    settings: Settings = request.app.state.settings
    enforce_ai_rate_limit(
        settings=settings,
        user_id=user.id if user is not None else None,
        ip=request.client.host if request.client else None,
    )
    context = body.context.model_dump() if body.context is not None else None
    response = await ai_service.chat(
        session,
        request=request,
        settings=settings,
        user=user,
        question=body.question,
        session_id=body.session_id,
        context=context,
    )
    return ItemEnvelope(
        data=response,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get(
    "/sessions",
    response_model=ListEnvelope[ChatSessionOut],
    summary="List the current user's chat sessions",
)
async def list_sessions_endpoint(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ListEnvelope[ChatSessionOut]:
    items = await ai_service.list_sessions(session, user=user)
    return ListEnvelope(data=items, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ListEnvelope[ChatMessageOut],
    summary="List messages in one owned chat session",
)
async def list_messages_endpoint(
    request: Request,
    session_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ListEnvelope[ChatMessageOut]:
    items = await ai_service.get_session_messages(
        session,
        user=user,
        session_id=session_id,
    )
    return ListEnvelope(data=items, meta=Meta(request_id=get_request_id(request)))
