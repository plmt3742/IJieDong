"""Indicator response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IndicatorOut(BaseModel):
    """Indicator metadata, including applicability and presentation hints."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal indicator ID.")
    code: str = Field(..., description="Stable indicator code.")
    name: str = Field(..., description="Indicator display name.")
    unit: str = Field(..., description="Measurement unit, or a text marker for long text.")
    value_type: str = Field(..., description="long_text, decimal, integer, or currency.")
    category: str | None = Field(None, description="Indicator category such as 人口 or 经济.")
    applicable_levels: list[str] = Field(
        ...,
        description="Region levels this indicator applies to.",
    )
    applicable_region_categories: list[str] | None = Field(
        None,
        description="Region categories this indicator applies to; null means all.",
    )
    aggregation: str = Field(..., description="Aggregation hint.")
    precision: int = Field(..., ge=0, description="Decimal places for display.")
    max_length: int | None = Field(None, ge=1, description="Maximum text length, if applicable.")
    direction: str = Field(..., description="Direction hint such as neutral or higher_is_better.")
    description: str | None = Field(None, description="Definition and calculation notes.")
    sort_order: int = Field(..., description="Display order.")
    enabled: bool = Field(..., description="Whether the indicator is enabled.")
    status: str = Field(..., description="Indicator lifecycle status.")
    version: int = Field(..., ge=1, description="Indicator metadata version.")
