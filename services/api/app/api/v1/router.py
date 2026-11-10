"""Version 1 API router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    auth,
    dashboard,
    data,
    exports,
    health,
    indicators,
    regions,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(regions.router)
api_router.include_router(indicators.router)
api_router.include_router(data.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(exports.router)
