"""Liveness and readiness endpoints.

``/health`` never touches the database. ``/ready`` runs ``SELECT 1`` and returns
503 with a ``NOT_READY`` error payload when the database is unreachable.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import error_payload
from app.core.request_id import get_request_id
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def _meta(request: Request) -> dict[str, str]:
    return {"request_id": get_request_id(request)}


@router.get("/health", summary="Liveness probe")
async def health(request: Request) -> JSONResponse:
    return JSONResponse(status_code=200, content={"data": {"status": "ok"}, "meta": _meta(request)})


@router.get("/ready", summary="Readiness probe")
async def ready(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    request_id = get_request_id(request)
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Readiness probe failed request_id=%s", request_id, exc_info=True)
        return JSONResponse(
            status_code=503,
            content=error_payload(
                code="NOT_READY",
                message="Database is not ready",
                request_id=request_id,
            ),
        )
    return JSONResponse(
        status_code=200,
        content={"data": {"status": "ready"}, "meta": {"request_id": request_id}},
    )
