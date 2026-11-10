"""Administrative endpoints for applications, users, audit logs, and imports."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.core.security import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.admin import (
    ApplicationOut,
    ApproveOut,
    ApproveRequest,
    AuditLogOut,
    ImportErrorsOut,
    ImportJobOut,
    RejectRequest,
    UserAdminOut,
    UserUpdateRequest,
)
from app.schemas.common import ItemEnvelope, Meta, PageEnvelope, PageMeta
from app.services import auth_service, import_service

router = APIRouter(prefix="/admin", tags=["admin"])

ApplicationStatus = Literal["pending", "approved", "rejected"]
UserRole = Literal["admin", "editor", "viewer", "approver"]
UserAccountStatus = Literal["active", "disabled"]


def _page_meta(request: Request, *, page: int, page_size: int, total: int) -> PageMeta:
    return PageMeta(
        request_id=get_request_id(request),
        page=page,
        page_size=page_size,
        total=total,
        has_next=page * page_size < total,
    )


@router.get(
    "/applications",
    response_model=PageEnvelope[ApplicationOut],
    summary="List account applications",
)
async def list_applications_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "approver"))],
    session: AsyncSession = Depends(get_db),
    status: Annotated[ApplicationStatus | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageEnvelope[ApplicationOut]:
    items, total = await auth_service.list_applications(
        session,
        status=status,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PageEnvelope(
        data=items,
        meta=_page_meta(request, page=page, page_size=page_size, total=total),
    )


@router.post(
    "/applications/{application_id}/approve",
    response_model=ItemEnvelope[ApproveOut],
    summary="Approve an application and create the account",
)
async def approve_application_endpoint(
    application_id: int,
    payload: ApproveRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "approver"))],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ApproveOut]:
    result = await auth_service.approve_application(
        session,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
        request=request,
    )
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.post(
    "/applications/{application_id}/reject",
    response_model=ItemEnvelope[ApplicationOut],
    summary="Reject an application",
)
async def reject_application_endpoint(
    application_id: int,
    payload: RejectRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "approver"))],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ApplicationOut]:
    result = await auth_service.reject_application(
        session,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
        request=request,
    )
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get("/users", response_model=PageEnvelope[UserAdminOut], summary="List users")
async def list_users_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: AsyncSession = Depends(get_db),
    role: Annotated[UserRole | None, Query()] = None,
    status: Annotated[UserAccountStatus | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageEnvelope[UserAdminOut]:
    items, total = await auth_service.list_users(
        session,
        role=role,
        status=status,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PageEnvelope(
        data=items,
        meta=_page_meta(request, page=page, page_size=page_size, total=total),
    )


@router.patch(
    "/users/{user_id}",
    response_model=ItemEnvelope[UserAdminOut],
    summary="Update a user role, status, unit, or display name",
)
async def update_user_endpoint(
    user_id: int,
    payload: UserUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[UserAdminOut]:
    result = await auth_service.update_user(
        session,
        user_id=user_id,
        payload=payload,
        current_user=current_user,
        request=request,
    )
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get(
    "/audit-logs",
    response_model=PageEnvelope[AuditLogOut],
    summary="List audit logs",
)
async def list_audit_logs_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: AsyncSession = Depends(get_db),
    action: Annotated[str | None, Query(max_length=64)] = None,
    user_id: Annotated[int | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageEnvelope[AuditLogOut]:
    items, total = await auth_service.list_audit_logs(
        session,
        action=action,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return PageEnvelope(
        data=items,
        meta=_page_meta(request, page=page, page_size=page_size, total=total),
    )


@router.post(
    "/imports",
    response_model=ItemEnvelope[ImportJobOut],
    summary="Import an Excel workbook",
)
async def create_import_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(require_roles("editor", "admin"))],
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    mode: Annotated[str, Form()] = "atomic",
    source_id: Annotated[int | None, Form()] = None,
) -> ItemEnvelope[ImportJobOut]:
    if mode not in {"atomic", "partial"}:
        raise AppError(
            "VALIDATION_ERROR",
            "mode must be atomic or partial",
            status_code=422,
            details={"mode": mode},
        )
    content = await file.read()
    result = await import_service.run_import(
        session,
        filename=file.filename,
        content=content,
        mode=mode,
        source_id=source_id,
        current_user=current_user,
        request=request,
    )
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get(
    "/imports",
    response_model=PageEnvelope[ImportJobOut],
    summary="List import jobs",
)
async def list_imports_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(require_roles("editor", "admin"))],
    session: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageEnvelope[ImportJobOut]:
    items, total = await import_service.list_import_jobs(
        session,
        page=page,
        page_size=page_size,
    )
    return PageEnvelope(
        data=items,
        meta=_page_meta(request, page=page, page_size=page_size, total=total),
    )


@router.get(
    "/imports/{job_id}",
    response_model=ItemEnvelope[ImportJobOut],
    summary="Get an import job",
)
async def get_import_endpoint(
    job_id: int,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("editor", "admin"))],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ImportJobOut]:
    result = await import_service.get_import_job(session, job_id)
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )


@router.get(
    "/imports/{job_id}/errors",
    response_model=ItemEnvelope[ImportErrorsOut],
    summary="Get the error report for an import job",
)
async def get_import_errors_endpoint(
    job_id: int,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("editor", "admin"))],
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[ImportErrorsOut]:
    result = await import_service.get_import_errors(session, job_id)
    return ItemEnvelope(
        data=result,
        meta=Meta(request_id=get_request_id(request)),
    )
