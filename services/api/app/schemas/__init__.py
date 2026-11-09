"""Pydantic v2 response schemas for the read-only Demo v0 query APIs."""
from __future__ import annotations

from app.schemas.common import (
    CompareEnvelope,
    CompareMeta,
    ItemEnvelope,
    ListEnvelope,
    Meta,
    PageEnvelope,
    PageMeta,
    RankEnvelope,
    RankMeta,
)
from app.schemas.dashboard import DashboardMetricOut, DashboardOverviewOut
from app.schemas.data_value import CompareItemOut, DataValueOut, RankItemOut
from app.schemas.indicator import IndicatorOut
from app.schemas.region import (
    ProfileMetricOut,
    RegionDetailOut,
    RegionOut,
    RegionProfileOut,
    RegionTreeOut,
)

__all__ = [
    "CompareEnvelope",
    "CompareItemOut",
    "CompareMeta",
    "DashboardMetricOut",
    "DashboardOverviewOut",
    "DataValueOut",
    "IndicatorOut",
    "ItemEnvelope",
    "ListEnvelope",
    "Meta",
    "PageEnvelope",
    "PageMeta",
    "ProfileMetricOut",
    "RankEnvelope",
    "RankItemOut",
    "RankMeta",
    "RegionDetailOut",
    "RegionOut",
    "RegionProfileOut",
    "RegionTreeOut",
]
