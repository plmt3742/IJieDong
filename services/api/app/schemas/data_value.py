"""Data value, ranking, and comparison response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DataValueOut(BaseModel):
    """One observation joined with its region and indicator display fields."""

    id: int = Field(..., description="Observation ID.")
    region_id: int = Field(..., description="Region ID.")
    region_code: str = Field(..., description="Region code.")
    region_name: str = Field(..., description="Region display name.")
    region_level: str = Field(..., description="Region level.")
    region_category: str = Field(..., description="Region category.")
    indicator_id: int = Field(..., description="Indicator ID.")
    indicator_code: str = Field(..., description="Indicator code.")
    indicator_name: str = Field(..., description="Indicator display name.")
    unit: str = Field(..., description="Measurement unit.")
    period_year: int = Field(..., description="Data period year.")
    value_number: float | None = Field(
        None,
        description="Numeric value; null means no data and is never replaced with zero.",
    )
    value_text: str | None = Field(None, description="Text value for long-text indicators.")
    quality_status: str = Field(
        ...,
        description="missing, not_applicable, suppressed, estimated, provisional, or verified.",
    )
    status: str = Field(..., description="Publication status: draft, published, or archived.")
    updated_at: datetime = Field(..., description="Last update time of the observation.")


class RankItemOut(BaseModel):
    """One ranked region for a numeric indicator."""

    rank: int = Field(..., ge=1, description="1-based rank after filtering nulls.")
    region_id: int = Field(..., description="Region ID.")
    region_code: str = Field(..., description="Region code.")
    region_name: str = Field(..., description="Region display name.")
    value_number: float = Field(..., description="Numeric value.")
    unit: str = Field(..., description="Measurement unit.")


class CompareItemOut(BaseModel):
    """One region inside a comparison result, in the requested order."""

    region_id: int = Field(..., description="Region ID.")
    region_code: str = Field(..., description="Region code.")
    region_name: str = Field(..., description="Region display name.")
    value_number: float | None = Field(
        None,
        description="Numeric value; null means no published value.",
    )
    quality_status: str = Field(..., description="Quality status of the observation.")
    unit: str = Field(..., description="Measurement unit.")
    diff_from_first: float | None = Field(
        None,
        description="Value minus the first region value; null when either side is missing.",
    )
    diff_pct_from_first: float | None = Field(
        None,
        description="Percentage difference from the first region; null when not computable.",
    )
