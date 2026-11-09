"""Application errors and FastAPI exception handlers.

All client-facing errors share the contract shape::

    {"error": {"code": "...", "message": "...", "details": {}}, "request_id": "..."}

Unhandled exceptions are logged with a stack trace on the server, but clients only
receive a generic message so internal details never leak.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_id import get_request_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Recoverable application error that maps to the standard error payload."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard error body."""
    return {
        "error": {"code": code, "message": message, "details": details or {}},
        "request_id": request_id,
    }


def _request_id_header(request: Request) -> str:
    settings = getattr(request.app.state, "settings", None)
    return getattr(settings, "request_id_header", "X-Request-ID")


def _json_error(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        ),
        headers={_request_id_header(request): request_id},
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    return _json_error(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return _json_error(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": jsonable_encoder(exc.errors())},
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    message = str(exc.detail)
    if exc.status_code == 404:
        code = "NOT_FOUND"
        message = message if message and message != "Not Found" else "Resource not found"
    elif exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
        message = message if message and message != "Method Not Allowed" else "Method not allowed"
    else:
        code = "HTTP_ERROR"
    return _json_error(request, status_code=exc.status_code, code=code, message=message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    logger.exception("Unhandled error request_id=%s", request_id)
    return _json_error(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="Internal server error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the shared error handlers to an application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
