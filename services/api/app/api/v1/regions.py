"""Region query endpoints.

Read-only and anonymous in Demo v0. Roles and permissions arrive in B05.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.db.session import get_db
from app.schemas import (
    ItemEnvelope,
    Meta,
    PageEnvelope,
    PageMeta,
    RegionDetailOut,
    RegionOut,
    RegionProfileOut,
    RegionTreeOut,
)
from app.services import query_service

router = APIRouter(prefix="/regions", tags=["regions"])

RegionLevel = Literal["district", "town", "village"]
RegionCategory = Literal["administrative", "development_zone"]


@router.get(
    "",
    response_model=PageEnvelope[RegionOut],
    summary="List regions",
    description="Paginated region list filtered by level, parent, name, category, and enabled state.",
)
async def list_regions_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    level: Annotated[RegionLevel | None, Query(description="Region level filter.")] = None,
    parent_id: Annotated[int | None, Query(description="Parent region ID filter.")] = None,
    parent_code: Annotated[
        str | None,
        Query(max_length=64, description="Parent region code filter."),
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=128, description="Name contains filter."),
    ] = None,
    category: Annotated[
        RegionCategory | None,
        Query(description="Region category filter."),
    ] = None,
    enabled: Annotated[bool, Query(description="Filter by enabled state.")] = True,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> PageEnvelope[RegionOut]:
    items, total = await query_service.list_regions(
        session,
        level=level,
        parent_id=parent_id,
        parent_code=parent_code,
        q=q,
        category=category,
        enabled=enabled,
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


@router.get(
    "/tree",
    response_model=ItemEnvelope[RegionTreeOut],
    summary="Get region tree",
    description="Nested region tree starting at root_code, including up to depth edges.",
)
async def get_region_tree_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_db),
    root_code: Annotated[
        str,
        Query(min_length=1, max_length=64, description="Root region code."),
    ] = "JD",
    depth: Annotated[int, Query(ge=1, le=3, description="Number of edges below the root.")] = 2,
) -> ItemEnvelope[RegionTreeOut]:
    tree = await query_service.get_region_tree(session, root_code=root_code, depth=depth)
    return ItemEnvelope(data=tree, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/{region_id}",
    response_model=ItemEnvelope[RegionDetailOut],
    summary="Get region detail",
    description="Return one region with its parent summary. 404 when the region is missing.",
)
async def get_region_detail_endpoint(
    region_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[RegionDetailOut]:
    detail = await query_service.get_region_detail(session, region_id)
    return ItemEnvelope(data=detail, meta=Meta(request_id=get_request_id(request)))


@router.get(
    "/{region_id}/profile",
    response_model=ItemEnvelope[RegionProfileOut],
    summary="Get region profile",
    description=(
        "Return region text, applicable numeric metrics, and data freshness. "
        "Development zones omit farmland, forest, and village-count indicators; "
        "villages omit district-only indicators."
    ),
)
async def get_region_profile_endpoint(
    region_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ItemEnvelope[RegionProfileOut]:
    profile = await query_service.get_region_profile(session, region_id)
    return ItemEnvelope(data=profile, meta=Meta(request_id=get_request_id(request)))
