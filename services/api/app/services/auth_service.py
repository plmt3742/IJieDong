"""Authentication, account application, and user administration services."""
from __future__ import annotations

import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_initial_password,
    generate_status_token,
    hash_password,
    hash_status_token,
    mask_phone,
    verify_password,
)
from app.models import AuditLog, User, UserApplication
from app.schemas.admin import (
    ApplicationOut,
    ApproveOut,
    ApproveRequest,
    AuditLogOut,
    RejectRequest,
    UserAdminOut,
    UserUpdateRequest,
)
from app.schemas.auth import ApplicationStatusOut, ApplicationSubmitOut
from app.services.audit_service import write_audit

PRIVACY_NOTICE_VERSION = "v1"
ASSIGNABLE_ROLES = {"viewer", "editor", "approver", "admin"}
APPROVER_ROLES = {"admin", "approver"}


def _auth_invalid() -> AppError:
    return AppError(
        "AUTH_INVALID",
        "Invalid username or password",
        status_code=401,
    )


def _user_disabled() -> AppError:
    return AppError("USER_DISABLED", "User account is disabled", status_code=403)


def _forbidden(message: str = "Insufficient permissions") -> AppError:
    return AppError("FORBIDDEN", message, status_code=403)


def _not_found(resource: str, resource_id: int | str) -> AppError:
    return AppError(
        "NOT_FOUND",
        f"{resource} not found",
        status_code=404,
        details={"id": resource_id},
    )


async def login(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    request: Request,
    settings: Settings,
) -> tuple[User, str, int]:
    normalised = username.strip()
    user = (
        await session.execute(
            select(User).where(func.lower(User.username) == normalised.lower())
        )
    ).scalars().first()

    if user is None or not verify_password(password, user.password_hash):
        await write_audit(
            session,
            action="auth.login.failed",
            resource_type="user",
            resource_id=user.id if user is not None else None,
            detail={"username": normalised},
            request=request,
            user_id=user.id if user is not None else None,
        )
        await session.commit()
        raise _auth_invalid()

    if user.status != "active":
        await write_audit(
            session,
            action="auth.login.denied",
            resource_type="user",
            resource_id=user.id,
            detail={"reason": "user_disabled"},
            request=request,
            user_id=user.id,
        )
        await session.commit()
        raise _user_disabled()

    user.last_login_at = datetime.now(timezone.utc)
    await write_audit(
        session,
        action="auth.login.success",
        resource_type="user",
        resource_id=user.id,
        detail={"username": user.username, "role": user.role},
        request=request,
        user_id=user.id,
    )
    await session.commit()

    token, expires_in = create_access_token(
        user_id=user.id,
        role=user.role,
        token_version=user.token_version,
        settings=settings,
    )
    return user, token, expires_in


async def _next_application_no(session: AsyncSession) -> str:
    prefix = f"AP{datetime.now(timezone.utc):%Y%m%d}"
    existing = set(
        (
            await session.execute(
                select(UserApplication.application_no).where(
                    UserApplication.application_no.like(f"{prefix}%")
                )
            )
        ).scalars()
    )
    sequence = 1
    while f"{prefix}{sequence:03d}" in existing:
        sequence += 1
    return f"{prefix}{sequence:03d}"


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _request_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    return value[:512] if value else None


async def submit_application(
    session: AsyncSession,
    *,
    display_name: str,
    unit: str,
    phone: str,
    reason: str,
    privacy_consent: bool,
    request: Request,
) -> tuple[UserApplication, str]:
    if not privacy_consent:
        raise AppError("VALIDATION_ERROR", "privacy_consent must be true", status_code=422)

    existing_user = (
        await session.execute(select(User).where(User.phone == phone))
    ).scalars().first()
    if existing_user is not None:
        raise AppError(
            "APPLICATION_DUPLICATE",
            "A user account already exists for this phone number",
            status_code=409,
        )

    pending = (
        await session.execute(
            select(UserApplication).where(
                UserApplication.phone == phone,
                UserApplication.status == "pending",
            )
        )
    ).scalars().first()
    if pending is not None:
        raise AppError(
            "APPLICATION_DUPLICATE",
            "A pending application already exists for this phone number",
            status_code=409,
            details={"application_no": pending.application_no},
        )

    resubmit_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(UserApplication)
                .where(
                    UserApplication.phone == phone,
                    UserApplication.status == "rejected",
                )
            )
        ).scalar_one()
    )

    status_token = generate_status_token()
    application = UserApplication(
        application_no=await _next_application_no(session),
        display_name=display_name,
        unit=unit,
        phone=phone,
        reason=reason,
        status="pending",
        status_token_hash=hash_status_token(status_token),
        resubmit_count=resubmit_count,
        privacy_consent=True,
        privacy_notice_version=PRIVACY_NOTICE_VERSION,
        submitted_ip=_request_ip(request),
        submitted_user_agent=_request_user_agent(request),
    )
    session.add(application)
    await session.flush()

    await write_audit(
        session,
        action="application.submit",
        resource_type="user_application",
        resource_id=application.id,
        detail={
            "application_no": application.application_no,
            "phone_last4": phone[-4:],
        },
        request=request,
    )
    await session.commit()
    return application, status_token


async def get_application_status(
    session: AsyncSession,
    *,
    application_no: str,
    status_token: str,
) -> ApplicationStatusOut:
    application = (
        await session.execute(
            select(UserApplication).where(
                UserApplication.application_no == application_no
            )
        )
    ).scalars().first()
    if application is None or not application.status_token_hash:
        raise AppError("NOT_FOUND", "Application not found", status_code=404)
    if not hmac.compare_digest(
        application.status_token_hash,
        hash_status_token(status_token),
    ):
        raise AppError("NOT_FOUND", "Application not found", status_code=404)
    return ApplicationStatusOut(
        application_no=application.application_no,
        status=application.status,
        reject_reason=application.reject_reason,
        submitted_at=application.created_at,
        reviewed_at=application.reviewed_at,
    )


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    old_password: str,
    new_password: str,
    request: Request,
) -> None:
    if not verify_password(old_password, user.password_hash):
        raise AppError(
            "VALIDATION_ERROR",
            "old_password is incorrect",
            status_code=400,
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version = (user.token_version or 1) + 1
    await write_audit(
        session,
        action="user.password_change",
        resource_type="user",
        resource_id=user.id,
        detail={"token_version": user.token_version},
        request=request,
        user_id=user.id,
    )
    await session.commit()


def _application_out(application: UserApplication) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        application_no=application.application_no,
        display_name=application.display_name,
        unit=application.unit,
        phone=mask_phone(application.phone),
        status=application.status,
        resubmit_count=application.resubmit_count,
        submitted_at=application.created_at,
        reviewed_at=application.reviewed_at,
        reject_reason=application.reject_reason,
    )


async def list_applications(
    session: AsyncSession,
    *,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ApplicationOut], int]:
    conditions: list[ColumnElement[bool]] = []
    if status is not None:
        conditions.append(UserApplication.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                UserApplication.application_no.like(pattern),
                UserApplication.display_name.like(pattern),
                UserApplication.unit.like(pattern),
                UserApplication.phone.like(pattern),
            )
        )

    total = int(
        (
            await session.execute(
                select(func.count()).select_from(UserApplication).where(*conditions)
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(UserApplication)
            .where(*conditions)
            .order_by(UserApplication.created_at.desc(), UserApplication.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return [_application_out(row) for row in rows], total


async def approve_application(
    session: AsyncSession,
    *,
    application_id: int,
    payload: ApproveRequest,
    current_user: User,
    request: Request,
) -> ApproveOut:
    application = await session.get(UserApplication, application_id)
    if application is None:
        raise _not_found("Application", application_id)
    if application.status != "pending":
        raise AppError(
            "APPLICATION_NOT_PENDING",
            "Application has already been processed",
            status_code=409,
            details={"status": application.status},
        )
    if current_user.role not in APPROVER_ROLES:
        raise _forbidden()
    if current_user.role == "approver" and payload.role != "viewer":
        raise _forbidden("Approvers may only assign the viewer role")
    if payload.role not in ASSIGNABLE_ROLES:
        raise AppError("VALIDATION_ERROR", "Unsupported role", status_code=422)
    if current_user.phone and application.phone == current_user.phone:
        raise AppError(
            "CANNOT_APPROVE_SELF",
            "An approver cannot approve their own application",
            status_code=403,
        )

    existing_user = (
        await session.execute(
            select(User).where(
                or_(User.phone == application.phone, User.username == application.phone)
            )
        )
    ).scalars().first()
    if existing_user is not None:
        raise AppError(
            "USER_ALREADY_EXISTS",
            "A user with this phone number or username already exists",
            status_code=409,
        )

    initial_password = payload.initial_password or generate_initial_password()
    user = User(
        username=application.phone,
        password_hash=hash_password(initial_password),
        display_name=application.display_name,
        role=payload.role,
        status="active",
        unit=payload.unit or application.unit,
        phone=application.phone,
        must_change_password=True,
    )
    session.add(user)
    await session.flush()

    application.status = "approved"
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.now(timezone.utc)
    application.created_user_id = user.id
    application.reject_reason = None

    await write_audit(
        session,
        action="application.approve",
        resource_type="user_application",
        resource_id=application.id,
        detail={
            "application_no": application.application_no,
            "created_user_id": user.id,
            "role": payload.role,
            "note": payload.note,
            "phone_last4": application.phone[-4:],
        },
        request=request,
        user_id=current_user.id,
    )
    await session.commit()

    return ApproveOut(
        application_id=application.id,
        status=application.status,
        user_id=user.id,
        username=user.username,
        role=user.role,
        initial_password=initial_password,
    )


async def reject_application(
    session: AsyncSession,
    *,
    application_id: int,
    payload: RejectRequest,
    current_user: User,
    request: Request,
) -> ApplicationOut:
    application = await session.get(UserApplication, application_id)
    if application is None:
        raise _not_found("Application", application_id)
    if application.status != "pending":
        raise AppError(
            "APPLICATION_NOT_PENDING",
            "Application has already been processed",
            status_code=409,
            details={"status": application.status},
        )
    if current_user.role not in APPROVER_ROLES:
        raise _forbidden()

    application.status = "rejected"
    application.reject_reason = payload.reason
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.now(timezone.utc)

    await write_audit(
        session,
        action="application.reject",
        resource_type="user_application",
        resource_id=application.id,
        detail={
            "application_no": application.application_no,
            "reason": payload.reason,
            "phone_last4": application.phone[-4:],
        },
        request=request,
        user_id=current_user.id,
    )
    await session.commit()
    return _application_out(application)


def _user_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        unit=user.unit,
        phone=mask_phone(user.phone),
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


async def list_users(
    session: AsyncSession,
    *,
    role: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[UserAdminOut], int]:
    conditions: list[ColumnElement[bool]] = []
    if role is not None:
        conditions.append(User.role == role)
    if status is not None:
        conditions.append(User.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                User.username.like(pattern),
                User.display_name.like(pattern),
                User.unit.like(pattern),
                User.phone.like(pattern),
            )
        )

    total = int(
        (
            await session.execute(
                select(func.count()).select_from(User).where(*conditions)
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(User)
            .where(*conditions)
            .order_by(User.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return [_user_out(row) for row in rows], total


async def _has_other_active_admin(session: AsyncSession, exclude_id: int) -> bool:
    count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.role == "admin",
                    User.status == "active",
                    User.id != exclude_id,
                )
            )
        ).scalar_one()
    )
    return count > 0


async def update_user(
    session: AsyncSession,
    *,
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User,
    request: Request,
) -> UserAdminOut:
    user = await session.get(User, user_id)
    if user is None:
        raise _not_found("User", user_id)

    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    new_role = changes.get("role", user.role)
    new_status = changes.get("status", user.status)
    was_active_admin = user.role == "admin" and user.status == "active"
    will_be_active_admin = new_role == "admin" and new_status == "active"
    if was_active_admin and not will_be_active_admin:
        if not await _has_other_active_admin(session, user.id):
            raise AppError(
                "LAST_ADMIN_PROTECTED",
                "The last active administrator cannot be disabled or demoted",
                status_code=409,
            )

    before = {
        "role": user.role,
        "status": user.status,
        "unit": user.unit,
        "display_name": user.display_name,
    }
    for field, value in changes.items():
        setattr(user, field, value)

    action = "user.update"
    if new_role != before["role"]:
        action = "user.role_change"
        user.token_version = (user.token_version or 1) + 1
    elif new_status != before["status"]:
        action = "user.enable" if new_status == "active" else "user.disable"
        user.token_version = (user.token_version or 1) + 1

    after = {
        "role": user.role,
        "status": user.status,
        "unit": user.unit,
        "display_name": user.display_name,
    }
    await write_audit(
        session,
        action=action,
        resource_type="user",
        resource_id=user.id,
        detail={"before": before, "after": after},
        request=request,
        user_id=current_user.id,
    )
    await session.commit()
    return _user_out(user)


async def list_audit_logs(
    session: AsyncSession,
    *,
    action: str | None = None,
    user_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AuditLogOut], int]:
    conditions: list[ColumnElement[bool]] = []
    if action is not None:
        conditions.append(AuditLog.action == action)
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)

    total = int(
        (
            await session.execute(
                select(func.count()).select_from(AuditLog).where(*conditions)
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return [AuditLogOut.model_validate(row, from_attributes=True) for row in rows], total
