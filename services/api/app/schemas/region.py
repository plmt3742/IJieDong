"""Region response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegionOut(BaseModel):
    """One region in the three-level tree."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal region ID.")
    code: str = Field(..., description="Stable internal region code.")
    name: str = Field(..., description="Display name.")
    level: str = Field(..., description="district, town, or village.")
    category: str = Field(..., description="administrative or development_zone.")
    parent_id: int | None = Field(None, description="Parent region ID; null for the district.")
    sort_order: int = Field(..., description="Display order within the parent.")
    enabled: bool = Field(..., description="Whether the region is enabled for display.")


class RegionDetailOut(RegionOut):
    """Region detail with a compact parent summary."""

    parent: RegionOut | None = Field(None, description="Parent region summary, if any.")


class RegionTreeOut(BaseModel):
    """Nested region tree node."""

    id: int = Field(..., description="Internal region ID.")
    code: str = Field(..., description="Stable internal region code.")
    name: str = Field(..., description="Display name.")
    level: str = Field(..., description="district, town, or village.")
    category: str = Field(..., description="administrative or development_zone.")
    parent_id: int | None = Field(None, description="Parent region ID; null for the root.")
    sort_order: int = Field(..., description="Display order within the parent.")
    enabled: bool = Field(..., description="Whether the region is enabled for display.")
    children: list[RegionTreeOut] = Field(
        default_factory=list,
        description="Nested child regions up to the requested depth.",
    )


class ProfileMetricOut(BaseModel):
    """One numeric indicator shown on a region profile."""

    indicator_id: int = Field(..., description="Indicator ID.")
    code: str = Field(..., description="Indicator code.")
    name: str = Field(..., description="Indicator display name.")
    unit: str = Field(..., description="Measurement unit.")
    value_number: float | None = Field(
        None,
        description="Numeric value; null means no published value (never zero-filled).",
    )
    quality_status: str = Field(
        ...,
        description="missing, not_applicable, suppressed, estimated, provisional, or verified.",
    )
    period_year: int = Field(..., description="Data period year for this value.")


class RegionProfileOut(BaseModel):
    """Region profile: narrative text, numeric metrics, and data freshness."""

    region: RegionOut = Field(..., description="Region the profile belongs to.")
    parent: RegionOut | None = Field(None, description="Parent region summary, if any.")
    intro: str | None = Field(None, description="Region introduction text, if available.")
    feature: str | None = Field(None, description="Region feature text, if available.")
    metrics: list[ProfileMetricOut] = Field(
        default_factory=list,
        description="Numeric indicators applicable to this region and level.",
    )
    applicable_indicator_codes: list[str] = Field(
        default_factory=list,
        description="Indicator codes applicable by level and region category.",
    )
    data_as_of: datetime | None = Field(
        None,
        description="Latest data update or successful import time for this region.",
    )
