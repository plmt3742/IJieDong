"""Logging configuration for the API service.

Log lines include the current request ID when one is available. Configuration is
idempotent so repeated app factories (tests, reloads) do not stack handlers.
"""
from __future__ import annotations

import logging
import sys

from app.core.request_id import current_request_id

_HANDLER_MARKER = "_ijiedong_handler"
_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"


class RequestIDLogFilter(logging.Filter):
    """Populate ``record.request_id`` from the request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = current_request_id() or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, then only adjust the level."""
    global _CONFIGURED

    resolved_level = getattr(logging, level.strip().upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(resolved_level)

    if _CONFIGURED:
        return

    already_installed = any(
        getattr(handler, _HANDLER_MARKER, False) for handler in root.handlers
    )
    if not already_installed:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        handler.addFilter(RequestIDLogFilter())
        setattr(handler, _HANDLER_MARKER, True)
        root.addHandler(handler)

    _CONFIGURED = True
