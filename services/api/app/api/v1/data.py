"""Data value query, ranking, and comparison endpoints.

Read-only and anonymous in Demo v0. Roles and permissions arrive in B05.
Ranking and comparison accept numeric indicators only; text indicators return a
422 ``INDICATOR_NOT_NUMERIC`` error.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.db.session import get_db
from app.schemas import (
    CompareEnvelope,
    CompareItemOut,
    CompareMeta,
    DataValueOut,
    PageEnvelope,
    PageMeta,
    RankEnvelope,
    RankItemOut,
    RankMeta,
)
from app.services import query_service

router = APIRouter(prefix="/data-values", tags=["data-values"])

RegionLevel = Literal["district", "town", "village"]
SortOrder = Literal["asc", "desc"]
PublishStatus = Literal["published"]
QualityStatus = Literal[
    "missing",
    "not_applicable",
    "suppressed",
    "estimated",
    "provisional",
    "verified",
]


@router.get(
    "/rank",
    response_model=RankEnvelope[RankItemOut],
    summary="Rank regions by a numeric indicator",
    description=(
        "Rank published numeric values for one region level. Null values and "
        "missing/not_applicable/suppressed qualities are excluded. Text indicators "
        "return 422 INDICATOR_NOT_NUMERIC."
    ),
)
async def rank_data_values_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    indicator_id: Annotated[int | None, Query(description="Indicator ID.")] = None,
    indicator_code: Annotated[
        str | None,
        Query(max_length=64, description="Indicator code."),
    ] = None,
    period_year: Annotated[int, Query(ge=2000, le=2100, description="Data period year.")] = 2025,
    level: Annotated[RegionLevel, Query(description="Region level to rank.")] = "town",
    order: Annotated[SortOrder, Query(description="Sort order.")] = "desc",
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum ranked rows.")] = 10,
    include_development_zones: Annotated[
        bool,
        Query(description="Include development zones when ranking town level."),
    ] = False,
) -> RankEnvelope[RankItemOut]:
    items, indicator = await query_service.rank_data_values(
        session,
        indicator_id=indicator_id,
        indicator_code=indicator_code,
        period_year=period_year,
        level=level,
        order=order,
        limit=limit,
        include_development_zones=include_development_zones,
    )
    return RankEnvelope(
        data=items,
        meta=RankMeta(
            request_id=get_request_id(request),
            indicator_code=indicator.code,
            period_year=period_year,
            level=level,
            order=order,
            limit=limit,
            include_development_zones=include_development_zones,
        ),
    )


@router.get(
    "/compare",
    response_model=CompareEnvelope[CompareItemOut],
    summary="Compare regions by a numeric indicator",
    description=(
        "Compare 2-20 regions in the requested order. Missing values stay null; "
        "differences are only computed when both the region and first value are numeric."
    ),
)
async def compare_data_values_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    indicator_id: Annotated[int | None, Query(description="Indicator ID.")] = None,
    indicator_code: Annotated[
        str | None,
        Query(max_length=64, description="Indicator code."),
    ] = None,
    region_codes: Annotated[
        str | None,
        Query(description="Comma-separated region codes in display order."),
    ] = None,
    region_ids: Annotated[
        str | None,
        Query(description="Comma-separated region IDs in display order."),
    ] = None,
    period_year: Annotated[int, Query(ge=2000, le=2100, description="Data period year.")] = 2025,
) -> CompareEnvelope[CompareItemOut]:
    items, indicator = await query_service.compare_data_values(
        session,
        indicator_id=indicator_id,
        indicator_code=indicator_code,
        region_codes=region_codes,
        region_ids=region_ids,
        period_year=period_year,
    )
    return CompareEnvelope(
        data=items,
        meta=CompareMeta(
            request_id=get_request_id(request),
            indicator_code=indicator.code,
            period_year=period_year,
            requested_count=len(items),
        ),
    )


@router.get(
    "",
    response_model=PageEnvelope[DataValueOut],
    summary="List data values",
    description=(
        "Paginated observations joined with region and indicator fields. "
        "Null numeric values are preserved and never replaced with zero; an empty "
        "result set returns 200 with an empty data list."
    ),
)
async def list_data_values_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    region_id: Annotated[int | None, Query(description="Region ID filter.")] = None,
    region_code: Annotated[
        str | None,
        Query(max_length=64, description="Region code filter."),
    ] = None,
    indicator_id: Annotated[int | None, Query(description="Indicator ID filter.")] = None,
    indicator_code: Annotated[
        str | None,
        Query(max_length=64, description="Indicator code filter."),
    ] = None,
    period_year: Annotated[int, Query(ge=2000, le=2100, description="Data period year.")] = 2025,
    status: Annotated[PublishStatus, Query(description="Publication status filter.")] = "published",
    quality_status: Annotated[
        QualityStatus | None,
        Query(description="Data quality status filter."),
    ] = None,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> PageEnvelope[DataValueOut]:
    items, total = await query_service.list_data_values(
        session,
        region_id=region_id,
        region_code=region_code,
        indicator_id=indicator_id,
        indicator_code=indicator_code,
        period_year=period_year,
        status=status,
        quality_status=quality_status,
        page=page,
        page_size=page_size,
    )
    return PageEnvelope(
        data=items,
        meta=PageMeta(
            request_id=get_request_id(request),
            page=page,
            page_size=page_size,
            total=total,
            has_next=page * page_size < total,
        ),
    )
