"""Version 1 API router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import dashboard, data, health, indicators, regions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(regions.router)
api_router.include_router(indicators.router)
api_router.include_router(data.router)
api_router.include_router(dashboard.router)
