"""Dashboard query endpoints.

Read-only and anonymous in Demo v0. Roles and permissions arrive in B05.
The overview is district-level only; no town-level GDP is fabricated.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.db.session import get_db
from app.schemas import DashboardOverviewOut, ItemEnvelope, Meta
from app.services import query_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/overview",
    response_model=ItemEnvelope[DashboardOverviewOut],
    summary="Get dashboard overview",
    description=(
        "District-level core metrics for one period. Null values stay null with a "
        "quality_status; town_count counts enabled town-level regions."
    ),
)
async def get_dashboard_overview_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    period_year: Annotated[int, Query(ge=2000, le=2100, description="Data period year.")] = 2025,
) -> ItemEnvelope[DashboardOverviewOut]:
    overview = await query_service.get_dashboard_overview(session, period_year=period_year)
    return ItemEnvelope(data=overview, meta=Meta(request_id=get_request_id(request)))
