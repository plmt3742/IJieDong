"""Dashboard response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardMetricOut(BaseModel):
    """One core district-level metric."""

    code: str = Field(..., description="Indicator code.")
    label: str = Field(..., description="Display label taken from indicator metadata.")
    unit: str = Field(..., description="Measurement unit taken from indicator metadata.")
    value_number: float | None = Field(
        None,
        description="Numeric value; null means no published value (never zero-filled).",
    )
    quality_status: str = Field(..., description="Quality status of the value.")


class DashboardOverviewOut(BaseModel):
    """District-level overview for one data period."""

    period_year: int = Field(..., description="Data period year.")
    town_count: int = Field(..., ge=0, description="Number of enabled town-level regions.")
    data_as_of: datetime | None = Field(
        None,
        description="Latest data update or successful import time.",
    )
    metrics: list[DashboardMetricOut] = Field(
        ...,
        description="Core district metrics in a stable display order.",
    )
