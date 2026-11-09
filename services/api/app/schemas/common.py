"""Shared response envelopes and metadata schemas.

Every successful response uses ``{"data": ..., "meta": {...}}``. Errors keep the
shape defined in :mod:`app.core.errors`. Schemas here are generic so each
endpoint keeps a precise ``response_model`` without falling back to ``Any``.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Metadata shared by every response."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="Request correlation ID.")


class PageMeta(Meta):
    """Pagination metadata for list endpoints."""

    page: int = Field(..., ge=1, description="1-based page number.")
    page_size: int = Field(..., ge=1, description="Items requested per page.")
    total: int = Field(..., ge=0, description="Total rows matching the filters.")
    has_next: bool = Field(..., description="True when another page is available.")


class RankMeta(Meta):
    """Metadata describing how a ranking was produced."""

    indicator_code: str = Field(..., description="Indicator code used for ranking.")
    period_year: int = Field(..., description="Data period year.")
    level: str = Field(..., description="Region level ranked.")
    order: str = Field(..., description="Sort order: asc or desc.")
    limit: int = Field(..., ge=1, description="Maximum rows requested.")
    include_development_zones: bool = Field(
        ...,
        description="Whether development zones were included at town level.",
    )


class CompareMeta(Meta):
    """Metadata describing a comparison request."""

    indicator_code: str = Field(..., description="Indicator code compared.")
    period_year: int = Field(..., description="Data period year.")
    requested_count: int = Field(..., ge=2, description="Regions included in the comparison.")


class ItemEnvelope(BaseModel, Generic[T]):
    """Single-resource response envelope."""

    data: T
    meta: Meta


class ListEnvelope(BaseModel, Generic[T]):
    """Unpaginated list response envelope."""

    data: list[T]
    meta: Meta


class PageEnvelope(BaseModel, Generic[T]):
    """Paginated list response envelope."""

    data: list[T]
    meta: PageMeta


class RankEnvelope(BaseModel, Generic[T]):
    """Ranking response envelope."""

    data: list[T]
    meta: RankMeta


class CompareEnvelope(BaseModel, Generic[T]):
    """Comparison response envelope."""

    data: list[T]
    meta: CompareMeta
