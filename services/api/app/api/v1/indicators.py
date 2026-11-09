"""Indicator query endpoints.

Read-only and anonymous in Demo v0. Roles and permissions arrive in B05.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.db.session import get_db
from app.schemas import IndicatorOut, ItemEnvelope, ListEnvelope, Meta
from app.services import query_service

router = APIRouter(prefix="/indicators", tags=["indicators"])

RegionLevel = Literal["district", "town", "village"]


@router.get(
    "",
    response_model=ListEnvelope[IndicatorOut],
    summary="List indicators",
    description="Return enabled indicator metadata ordered by sort_order.",
)
async def list_indicators_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    level: Annotated[
        RegionLevel | None,
        Query(description="Only indicators applicable to this region level."),
    ] = None,
    category: Annotated[
        str | None,
        Query(max_length=32, description="Indicator category filter."),
    ] = None,
    enabled: Annotated[bool, Query(description="Filter by enabled state.")] = True,
) -> ListEnvelope[IndicatorOut]:
    items = await query_service.list_indicators(
        session,
        level=level,
        category=category,
        enabled=enabled,
    )
    return ListEnvelope(data=items, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/{indicator_id}",
    response_model=ItemEnvelope[IndicatorOut],
    summary="Get indicator detail",
    description="Return one indicator's metadata or 404 when it is missing.",
)
async def get_indicator_detail_endpoint(
    indicator_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[IndicatorOut]:
    detail = await query_service.get_indicator_detail(session, indicator_id)
    return ItemEnvelope(data=detail, meta=Meta(request_id=get_request_id(request)))
