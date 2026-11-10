"""Authentication and account-application endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    ApplicationStatusOut,
    ApplicationSubmitOut,
    ApplyRequest,
    ChangePasswordOut,
    ChangePasswordRequest,
    LoginData,
    LoginRequest,
    UserOut,
)
from app.schemas.common import ItemEnvelope, Meta
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ItemEnvelope[LoginData], summary="Log in")
async def login_endpoint(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[LoginData]:
    user, token, expires_in = await auth_service.login(
        session,
        username=payload.username,
        password=payload.password,
        request=request,
        settings=request.app.state.settings,
    )
    return ItemEnvelope(
        data=LoginData(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserOut.model_validate(user),
        ),
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get("/me", response_model=ItemEnvelope[UserOut], summary="Current user")
async def me_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ItemEnvelope[UserOut]:
    return ItemEnvelope(
        data=UserOut.model_validate(current_user),
        meta=Meta(request_id=get_request_id(request)),
    )


@router.post("/apply", response_model=ItemEnvelope[ApplicationSubmitOut], summary="Submit account application")
async def apply_endpoint(
    payload: ApplyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ApplicationSubmitOut]:
    application, status_token = await auth_service.submit_application(
        session,
        display_name=payload.display_name,
        unit=payload.unit,
        phone=payload.phone,
        reason=payload.reason,
        privacy_consent=payload.privacy_consent,
        request=request,
    )
    return ItemEnvelope(
        data=ApplicationSubmitOut(
            application_no=application.application_no,
            status=application.status,
            status_token=status_token,
            submitted_at=application.created_at,
        ),
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get(
    "/application-status",
    response_model=ItemEnvelope[ApplicationStatusOut],
    summary="Check application status",
)
async def application_status_endpoint(
    request: Request,
    application_no: Annotated[str, Query(min_length=1, max_length=32)],
    status_token: Annotated[str, Query(min_length=1, max_length=128)],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ApplicationStatusOut]:
    status = await auth_service.get_application_status(
        session,
        application_no=application_no,
        status_token=status_token,
    )
    return ItemEnvelope(
        data=status,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.post("/logout", status_code=204, summary="Log out")
async def logout_endpoint(
    current_user: Annotated[User, Depends(require_roles())],
) -> Response:
    return Response(status_code=204)


@router.post(
    "/change-password",
    response_model=ItemEnvelope[ChangePasswordOut],
    summary="Change the current password",
)
async def change_password_endpoint(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles())],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ChangePasswordOut]:
    await auth_service.change_password(
        session,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
        request=request,
    )
    return ItemEnvelope(
        data=ChangePasswordOut(),
        meta=Meta(request_id=get_request_id(request)),
    )
