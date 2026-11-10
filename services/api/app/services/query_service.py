"""Read-only query service for the Demo v0 public APIs.

The service owns all business filtering, joining, ranking, comparison, and
dashboard assembly. Routes stay thin: parse/validate query parameters, call one
service function, and wrap the result in the standard response envelope.

B04 is anonymous and read-only. Authentication, roles, and permissions are
implemented by B05 and are intentionally absent here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataValue, ImportJob, Indicator, Region
from app.schemas import (
    CompareItemOut,
    DashboardMetricOut,
    DashboardOverviewOut,
    DataValueOut,
    IndicatorOut,
    ProfileMetricOut,
    RankItemOut,
    RegionDetailOut,
    RegionOut,
    RegionProfileOut,
    RegionTreeOut,
)

DEFAULT_PERIOD_YEAR = 2025
PROFILE_TEXT_CODES = ("region_intro", "region_feature")
NON_NUMERIC_EXCLUDED_QUALITY = ("missing", "not_applicable", "suppressed")
DASHBOARD_METRIC_CODES = (
    "area",
    "population_resident",
    "population_household",
    "gdp",
    "budget_revenue",
    "admin_village_count",
)
DASHBOARD_METRIC_LABELS = {
    "area": "区域面积",
    "population_resident": "常住人口",
    "population_household": "户籍人口数",
    "gdp": "地区生产总值",
    "budget_revenue": "地方一般公共预算收入",
    "admin_village_count": "行政村数量",
}
DASHBOARD_METRIC_UNITS = {
    "area": "平方公里",
    "population_resident": "人",
    "population_household": "人",
    "gdp": "亿元",
    "budget_revenue": "亿元",
    "admin_village_count": "个",
}


def _number(value: Decimal | int | float | None) -> float | None:
    """Convert a database numeric to a JSON number without fabricating zeros."""
    if value is None:
        return None
    return float(value)


def _region_out(region: Region) -> RegionOut:
    return RegionOut.model_validate(region)


def _as_naive_utc(value: datetime | None) -> datetime | None:
    """Normalise timezone-aware values so SQLite and PostgreSQL compare safely."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _max_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _region_not_found(region_id: int) -> AppError:
    return AppError(
        "NOT_FOUND",
        "Region not found",
        status_code=404,
        details={"region_id": region_id},
    )


def _indicator_not_found(details: dict[str, object]) -> AppError:
    return AppError(
        "NOT_FOUND",
        "Indicator not found",
        status_code=404,
        details=details,
    )


def _indicator_not_numeric(indicator: Indicator) -> AppError:
    return AppError(
        "INDICATOR_NOT_NUMERIC",
        "Text indicators cannot be ranked or compared",
        status_code=422,
        details={"indicator_code": indicator.code, "value_type": indicator.value_type},
    )


def _is_numeric(indicator: Indicator) -> bool:
    return indicator.value_type != "long_text"


def _is_applicable(indicator: Indicator, region: Region) -> bool:
    """Mirror the seed/import applicability rules for one region."""
    if not indicator.enabled:
        return False
    if region.level not in (indicator.applicable_levels or []):
        return False
    categories = indicator.applicable_region_categories
    if categories and region.category not in categories:
        return False
    if indicator.code == "gdp":
        return region.level == "district" or region.category == "development_zone"
    return True


async def _resolve_indicator(
    session: AsyncSession,
    *,
    indicator_id: int | None,
    indicator_code: str | None,
) -> Indicator | None:
    if indicator_id is not None:
        return await session.get(Indicator, indicator_id)
    if indicator_code:
        return (
            await session.execute(select(Indicator).where(Indicator.code == indicator_code))
        ).scalars().first()
    return None


async def _latest_data_as_of(
    session: AsyncSession,
    region_id: int | None = None,
) -> datetime | None:
    value_stmt = select(func.max(DataValue.updated_at))
    if region_id is not None:
        value_stmt = value_stmt.where(DataValue.region_id == region_id)
    value_at = (await session.execute(value_stmt)).scalar_one()
    import_at = (
        await session.execute(
            select(func.max(ImportJob.finished_at)).where(
                ImportJob.status.in_(("success", "partial"))
            )
        )
    ).scalar_one()
    return _max_datetime(_as_naive_utc(value_at), _as_naive_utc(import_at))


async def list_regions(
    session: AsyncSession,
    *,
    level: str | None = None,
    parent_id: int | None = None,
    parent_code: str | None = None,
    q: str | None = None,
    category: str | None = None,
    enabled: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RegionOut], int]:
    """Return one page of regions plus the total row count."""
    conditions: list[ColumnElement[bool]] = [Region.enabled.is_(enabled)]
    if level is not None:
        conditions.append(Region.level == level)
    if parent_id is not None:
        conditions.append(Region.parent_id == parent_id)
    if parent_code:
        parent_ids = select(Region.id).where(Region.code == parent_code)
        conditions.append(Region.parent_id.in_(parent_ids))
    if q:
        conditions.append(Region.name.contains(q))
    if category is not None:
        conditions.append(Region.category == category)

    total = int(
        (
            await session.execute(
                select(func.count()).select_from(Region).where(*conditions)
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(Region)
            .where(*conditions)
            .order_by(Region.sort_order, Region.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return [_region_out(region) for region in rows], total


async def get_region_detail(session: AsyncSession, region_id: int) -> RegionDetailOut:
    """Return one region with its parent summary."""
    region = await session.get(Region, region_id)
    if region is None:
        raise _region_not_found(region_id)
    parent = await session.get(Region, region.parent_id) if region.parent_id else None
    payload = _region_out(region).model_dump()
    payload["parent"] = _region_out(parent) if parent is not None else None
    return RegionDetailOut(**payload)


async def get_region_tree(
    session: AsyncSession,
    *,
    root_code: str = "JD",
    depth: int = 2,
) -> RegionTreeOut:
    """Return a nested tree starting at ``root_code`` up to ``depth`` edges."""
    root = (
        await session.execute(select(Region).where(Region.code == root_code))
    ).scalars().first()
    if root is None:
        raise AppError(
            "NOT_FOUND",
            "Root region not found",
            status_code=404,
            details={"root_code": root_code},
        )

    rows = (
        await session.execute(select(Region).order_by(Region.sort_order, Region.id))
    ).scalars().all()
    children_by_parent: dict[int | None, list[Region]] = {}
    for region in rows:
        children_by_parent.setdefault(region.parent_id, []).append(region)

    def build(region: Region, remaining_depth: int) -> RegionTreeOut:
        children = []
        if remaining_depth > 0:
            for child in children_by_parent.get(region.id, []):
                children.append(build(child, remaining_depth - 1))
        return RegionTreeOut(
            id=region.id,
            code=region.code,
            name=region.name,
            level=region.level,
            category=region.category,
            parent_id=region.parent_id,
            sort_order=region.sort_order,
            enabled=region.enabled,
            children=children,
        )

    return build(root, depth)


async def get_region_profile(session: AsyncSession, region_id: int) -> RegionProfileOut:
    """Return narrative text, applicable numeric metrics, and freshness metadata."""
    region = await session.get(Region, region_id)
    if region is None:
        raise _region_not_found(region_id)
    parent = await session.get(Region, region.parent_id) if region.parent_id else None

    rows = (
        await session.execute(
            select(DataValue, Indicator)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                DataValue.region_id == region.id,
                DataValue.status == "published",
            )
            .order_by(DataValue.period_year, DataValue.id)
        )
    ).all()
    latest_year = max((value.period_year for value, _ in rows), default=DEFAULT_PERIOD_YEAR)
    latest_values: dict[str, tuple[DataValue, Indicator]] = {
        indicator.code: (value, indicator)
        for value, indicator in rows
        if value.period_year == latest_year
    }

    applicable = [
        indicator
        for indicator in (
            await session.execute(
                select(Indicator)
                .where(Indicator.enabled.is_(True))
                .order_by(Indicator.sort_order, Indicator.id)
            )
        ).scalars().all()
        if _is_applicable(indicator, region)
    ]

    metrics: list[ProfileMetricOut] = []
    for indicator in applicable:
        if not _is_numeric(indicator):
            continue
        entry = latest_values.get(indicator.code)
        value = entry[0] if entry is not None else None
        metrics.append(
            ProfileMetricOut(
                indicator_id=indicator.id,
                code=indicator.code,
                name=indicator.name,
                unit=indicator.unit,
                value_number=_number(value.value_number) if value is not None else None,
                quality_status=value.quality_status if value is not None else "missing",
                period_year=latest_year,
            )
        )

    def text_value(code: str) -> str | None:
        entry = latest_values.get(code)
        return entry[0].value_text if entry is not None else None

    return RegionProfileOut(
        region=_region_out(region),
        parent=_region_out(parent) if parent is not None else None,
        intro=text_value("region_intro"),
        feature=text_value("region_feature"),
        metrics=metrics,
        applicable_indicator_codes=[indicator.code for indicator in applicable],
        data_as_of=await _latest_data_as_of(session, region_id=region.id),
    )


async def list_indicators(
    session: AsyncSession,
    *,
    level: str | None = None,
    category: str | None = None,
    value_type: str | None = None,
    enabled: bool = True,
) -> list[IndicatorOut]:
    """Return indicator metadata ordered by display order."""
    conditions: list[ColumnElement[bool]] = [Indicator.enabled.is_(enabled)]
    if category is not None:
        conditions.append(Indicator.category == category)
    if value_type is not None:
        conditions.append(Indicator.value_type == value_type)
    rows = (
        await session.execute(
            select(Indicator).where(*conditions).order_by(Indicator.sort_order, Indicator.id)
        )
    ).scalars().all()
    if level is not None:
        rows = [row for row in rows if level in (row.applicable_levels or [])]
    return [IndicatorOut.model_validate(row) for row in rows]


async def get_indicator_detail(session: AsyncSession, indicator_id: int) -> IndicatorOut:
    """Return one indicator or raise a 404 AppError."""
    indicator = await session.get(Indicator, indicator_id)
    if indicator is None:
        raise _indicator_not_found({"indicator_id": indicator_id})
    return IndicatorOut.model_validate(indicator)


async def list_data_values(
    session: AsyncSession,
    *,
    region_id: int | None = None,
    region_code: str | None = None,
    indicator_id: int | None = None,
    indicator_code: str | None = None,
    period_year: int = DEFAULT_PERIOD_YEAR,
    status: str = "published",
    quality_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DataValueOut], int]:
    """Return one page of observations joined with region and indicator fields."""
    conditions: list[ColumnElement[bool]] = [
        DataValue.period_year == period_year,
        DataValue.status == status,
    ]
    if quality_status is not None:
        conditions.append(DataValue.quality_status == quality_status)
    if region_id is not None:
        conditions.append(DataValue.region_id == region_id)
    if region_code:
        conditions.append(Region.code == region_code)
    if indicator_id is not None:
        conditions.append(DataValue.indicator_id == indicator_id)
    if indicator_code:
        conditions.append(Indicator.code == indicator_code)

    count_stmt = (
        select(func.count())
        .select_from(DataValue)
        .join(Region, DataValue.region_id == Region.id)
        .join(Indicator, DataValue.indicator_id == Indicator.id)
        .where(*conditions)
    )
    total = int((await session.execute(count_stmt)).scalar_one())

    rows = (
        await session.execute(
            select(DataValue, Region, Indicator)
            .join(Region, DataValue.region_id == Region.id)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(*conditions)
            .order_by(DataValue.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()

    items = [
        DataValueOut(
            id=value.id,
            region_id=region.id,
            region_code=region.code,
            region_name=region.name,
            region_level=region.level,
            region_category=region.category,
            indicator_id=indicator.id,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            unit=indicator.unit,
            period_year=value.period_year,
            value_number=_number(value.value_number),
            value_text=value.value_text,
            quality_status=value.quality_status,
            status=value.status,
            updated_at=_as_naive_utc(value.updated_at) or value.updated_at,
        )
        for value, region, indicator in rows
    ]
    return items, total


async def rank_data_values(
    session: AsyncSession,
    *,
    indicator_id: int | None = None,
    indicator_code: str | None = None,
    period_year: int = DEFAULT_PERIOD_YEAR,
    level: str = "town",
    order: str = "desc",
    limit: int = 10,
    include_development_zones: bool = False,
) -> tuple[list[RankItemOut], Indicator]:
    """Rank published numeric values for one level, excluding nulls and gaps."""
    if indicator_id is None and not indicator_code:
        raise AppError(
            "VALIDATION_ERROR",
            "indicator_id or indicator_code is required",
            status_code=422,
        )
    indicator = await _resolve_indicator(
        session,
        indicator_id=indicator_id,
        indicator_code=indicator_code,
    )
    if indicator is None:
        raise _indicator_not_found(
            {"indicator_id": indicator_id, "indicator_code": indicator_code}
        )
    if not _is_numeric(indicator):
        raise _indicator_not_numeric(indicator)

    conditions: list[ColumnElement[bool]] = [
        DataValue.indicator_id == indicator.id,
        DataValue.period_year == period_year,
        DataValue.status == "published",
        DataValue.value_number.is_not(None),
        DataValue.quality_status.not_in(NON_NUMERIC_EXCLUDED_QUALITY),
        Region.level == level,
        Region.enabled.is_(True),
    ]
    if level == "town" and not include_development_zones:
        conditions.append(Region.category == "administrative")

    value_order = DataValue.value_number.desc() if order == "desc" else DataValue.value_number.asc()
    rows = (
        await session.execute(
            select(DataValue.value_number, Region.id, Region.code, Region.name)
            .join(Region, DataValue.region_id == Region.id)
            .where(*conditions)
            .order_by(value_order, Region.sort_order, Region.id)
            .limit(limit)
        )
    ).all()

    items = [
        RankItemOut(
            rank=index,
            region_id=region_id,
            region_code=region_code,
            region_name=region_name,
            value_number=float(value_number),
            unit=indicator.unit,
        )
        for index, (value_number, region_id, region_code, region_name) in enumerate(rows, start=1)
    ]
    return items, indicator


def _parse_int_csv(raw: str | None, field_name: str) -> list[int]:
    if not raw:
        return []
    try:
        values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise AppError(
            "VALIDATION_ERROR",
            f"{field_name} must be a comma-separated list of integers",
            status_code=422,
            details={field_name: raw},
        ) from exc
    return list(dict.fromkeys(values))


async def compare_data_values(
    session: AsyncSession,
    *,
    indicator_id: int | None = None,
    indicator_code: str | None = None,
    region_codes: str | None = None,
    region_ids: str | None = None,
    period_year: int = DEFAULT_PERIOD_YEAR,
) -> tuple[list[CompareItemOut], Indicator]:
    """Compare one numeric indicator across 2-20 regions in the requested order."""
    if indicator_id is None and not indicator_code:
        raise AppError(
            "VALIDATION_ERROR",
            "indicator_id or indicator_code is required",
            status_code=422,
        )
    indicator = await _resolve_indicator(
        session,
        indicator_id=indicator_id,
        indicator_code=indicator_code,
    )
    if indicator is None:
        raise _indicator_not_found(
            {"indicator_id": indicator_id, "indicator_code": indicator_code}
        )
    if not _is_numeric(indicator):
        raise _indicator_not_numeric(indicator)

    parsed_ids = _parse_int_csv(region_ids, "region_ids")
    parsed_codes = [part.strip() for part in (region_codes or "").split(",") if part.strip()]
    parsed_codes = list(dict.fromkeys(parsed_codes))
    if not parsed_ids and not parsed_codes:
        raise AppError(
            "VALIDATION_ERROR",
            "region_codes or region_ids is required",
            status_code=422,
        )

    regions: list[Region] = []
    if parsed_ids:
        rows = (
            await session.execute(select(Region).where(Region.id.in_(parsed_ids)))
        ).scalars().all()
        by_id = {region.id: region for region in rows}
        missing = [region_id for region_id in parsed_ids if region_id not in by_id]
        if missing:
            raise AppError(
                "REGION_NOT_FOUND",
                "Region not found",
                status_code=404,
                details={"region_ids": missing},
            )
        regions = [by_id[region_id] for region_id in parsed_ids]
    else:
        rows = (
            await session.execute(select(Region).where(Region.code.in_(parsed_codes)))
        ).scalars().all()
        by_code = {region.code: region for region in rows}
        missing_codes = [code for code in parsed_codes if code not in by_code]
        if missing_codes:
            raise AppError(
                "REGION_NOT_FOUND",
                "Region not found",
                status_code=404,
                details={"region_codes": missing_codes},
            )
        regions = [by_code[code] for code in parsed_codes]

    if len(regions) < 2 or len(regions) > 20:
        raise AppError(
            "COMPARE_REGION_COUNT_INVALID",
            "Compare requires between 2 and 20 regions",
            status_code=422,
            details={"count": len(regions)},
        )

    value_rows = (
        await session.execute(
            select(DataValue)
            .where(
                DataValue.indicator_id == indicator.id,
                DataValue.period_year == period_year,
                DataValue.status == "published",
                DataValue.region_id.in_([region.id for region in regions]),
            )
            .order_by(DataValue.id)
        )
    ).scalars().all()
    values_by_region = {value.region_id: value for value in value_rows}

    first_entry = values_by_region.get(regions[0].id)
    first_value = _number(first_entry.value_number) if first_entry is not None else None

    items: list[CompareItemOut] = []
    for region in regions:
        entry = values_by_region.get(region.id)
        value_number = _number(entry.value_number) if entry is not None else None
        quality_status = entry.quality_status if entry is not None else "missing"

        diff_from_first: float | None = None
        diff_pct_from_first: float | None = None
        if value_number is not None and first_value is not None:
            diff_from_first = round(value_number - first_value, 4)
            if first_value != 0:
                diff_pct_from_first = round((value_number - first_value) / first_value * 100, 2)

        items.append(
            CompareItemOut(
                region_id=region.id,
                region_code=region.code,
                region_name=region.name,
                value_number=value_number,
                quality_status=quality_status,
                unit=indicator.unit,
                diff_from_first=diff_from_first,
                diff_pct_from_first=diff_pct_from_first,
            )
        )
    return items, indicator


async def get_dashboard_overview(
    session: AsyncSession,
    *,
    period_year: int = DEFAULT_PERIOD_YEAR,
) -> DashboardOverviewOut:
    """Build the district-level overview without fabricating town-level GDP."""
    district = (
        await session.execute(
            select(Region)
            .where(Region.level == "district", Region.category == "administrative")
            .order_by(Region.sort_order, Region.id)
        )
    ).scalars().first()
    if district is None:
        raise AppError(
            "NOT_FOUND",
            "District region not found",
            status_code=404,
        )

    indicators = (
        await session.execute(
            select(Indicator).where(Indicator.code.in_(DASHBOARD_METRIC_CODES))
        )
    ).scalars().all()
    indicators_by_code = {indicator.code: indicator for indicator in indicators}

    values = (
        await session.execute(
            select(DataValue, Indicator)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                DataValue.region_id == district.id,
                DataValue.period_year == period_year,
                DataValue.status == "published",
                Indicator.code.in_(DASHBOARD_METRIC_CODES),
            )
            .order_by(DataValue.id)
        )
    ).all()
    values_by_code = {indicator.code: value for value, indicator in values}

    metrics = []
    for code in DASHBOARD_METRIC_CODES:
        indicator = indicators_by_code.get(code)
        value = values_by_code.get(code)
        metrics.append(
            DashboardMetricOut(
                code=code,
                label=indicator.name if indicator is not None else DASHBOARD_METRIC_LABELS[code],
                unit=indicator.unit if indicator is not None else DASHBOARD_METRIC_UNITS[code],
                value_number=_number(value.value_number) if value is not None else None,
                quality_status=value.quality_status if value is not None else "missing",
            )
        )

    town_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Region)
                .where(Region.level == "town", Region.enabled.is_(True))
            )
        ).scalar_one()
    )

    district_indicators = (
        await session.execute(select(Indicator).where(Indicator.enabled.is_(True)))
    ).scalars().all()
    coverage_codes = [
        indicator.code
        for indicator in district_indicators
        if indicator.value_type != "long_text"
        and "district" in (indicator.applicable_levels or [])
    ]
    coverage: float | None = None
    if coverage_codes:
        covered_count = int(
            (
                await session.execute(
                    select(func.count(func.distinct(DataValue.indicator_id)))
                    .select_from(DataValue)
                    .join(Indicator, DataValue.indicator_id == Indicator.id)
                    .where(
                        DataValue.region_id == district.id,
                        DataValue.period_year == period_year,
                        DataValue.status == "published",
                        DataValue.value_number.is_not(None),
                        DataValue.quality_status.notin_(NON_NUMERIC_EXCLUDED_QUALITY),
                        Indicator.code.in_(coverage_codes),
                    )
                )
            ).scalar_one()
        )
        coverage = round(covered_count / len(coverage_codes) * 100, 1)

    return DashboardOverviewOut(
        period_year=period_year,
        town_count=town_count,
        coverage=coverage,
        data_as_of=await _latest_data_as_of(session, region_id=district.id),
        metrics=metrics,
    )
