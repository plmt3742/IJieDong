"""Password hashing, JWT helpers, phone masking, and role dependencies."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models import User

JWT_ALGORITHM = "HS256"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SCRYPT_SALT_BYTES = 16
STATUS_TOKEN_BYTES = 32
MIN_PASSWORD_LENGTH = 10

_PASSWORD_HASH_PREFIX = "scrypt"


class TokenError(Exception):
    """Raised when an access token is missing required claims or cannot be trusted."""


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: int
    role: str
    token_version: int


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return (
        f"{_PASSWORD_HASH_PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        prefix, n_raw, r_raw, p_raw, salt_hex, digest_hex = stored_hash.split("$")
        if prefix != _PASSWORD_HASH_PREFIX:
            return False
        n = int(n_raw)
        r = int(r_raw)
        p = int(p_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and any(char.isalpha() for char in password)
        and any(char.isdigit() for char in password)
    )


def hash_status_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_status_token() -> str:
    return secrets.token_urlsafe(STATUS_TOKEN_BYTES)


def generate_initial_password() -> str:
    return f"{secrets.token_urlsafe(9)}2025"


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return phone
    if len(phone) < 7:
        return "*" * len(phone)
    return f"{phone[:3]}****{phone[-4:]}"


def create_access_token(
    *,
    user_id: int,
    role: str,
    token_version: int,
    settings: Settings | None = None,
    expires_minutes: int | None = None,
) -> tuple[str, int]:
    resolved = settings or get_settings()
    minutes = (
        expires_minutes
        if expires_minutes is not None
        else resolved.access_token_expire_minutes
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "ver": token_version,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=minutes),
    }
    token = jwt.encode(payload, resolved.jwt_secret_value, algorithm=JWT_ALGORITHM)
    return token, int(timedelta(minutes=minutes).total_seconds())


def decode_access_token(
    token: str,
    settings: Settings | None = None,
) -> AccessTokenPayload:
    resolved = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            resolved.jwt_secret_value,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid") from exc
    try:
        user_id = int(payload["sub"])
        role = str(payload["role"])
        token_version = int(payload.get("ver", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("invalid") from exc
    return AccessTokenPayload(
        user_id=user_id,
        role=role,
        token_version=token_version,
    )


bearer_scheme = HTTPBearer(auto_error=False)


def _auth_required() -> AppError:
    return AppError("AUTH_REQUIRED", "Authentication is required", status_code=401)


def _auth_invalid() -> AppError:
    return AppError("AUTH_INVALID", "Authentication token is invalid or expired", status_code=401)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise _auth_required()
    settings: Settings = request.app.state.settings
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except TokenError as exc:
        raise _auth_invalid() from exc

    user = await session.get(User, payload.user_id)
    if user is None:
        raise _auth_invalid()
    if user.status != "active":
        raise AppError("USER_DISABLED", "User account is disabled", status_code=403)
    if user.token_version != payload.token_version:
        raise _auth_invalid()
    return user


def require_roles(*roles: str):
    async def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if roles and current_user.role not in roles:
            raise AppError("FORBIDDEN", "Insufficient permissions", status_code=403)
        return current_user

    return dependency
