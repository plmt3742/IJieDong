"""Request ID middleware and context helpers.

Every request gets a correlation ID: either the incoming header value when it is
present and safe, or a freshly generated UUID4. The ID is stored on
``request.state.request_id``, kept in a context variable for logging, and echoed
back in the configured response header.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REQUEST_ID_STATE_KEY = "request_id"
MAX_REQUEST_ID_LENGTH = 128

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    """Return the request ID bound to the current execution context, if any."""
    return _request_id_ctx.get()


def get_request_id(request: Request) -> str:
    """Return the request ID for ``request``, falling back to ``-``."""
    value = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    if value:
        return str(value)
    return current_request_id() or "-"


def _normalise(value: str | None) -> str | None:
    """Accept a caller-provided ID only when it is short, clean and non-empty."""
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > MAX_REQUEST_ID_LENGTH:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to the request state and the response headers."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = _normalise(request.headers.get(self.header_name)) or str(uuid.uuid4())
        request.state.request_id = request_id
        token: Token[str | None] = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[self.header_name] = request_id
        return response
