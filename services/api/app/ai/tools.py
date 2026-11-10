"""Read-only tool whitelist from spec 24 section 5.

Every tool takes only structured arguments, reads through SQLAlchemy, and returns
numbers copied from ``data_values``. No tool accepts SQL, JavaScript, URLs, or
file paths.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataValue, Indicator, Region, RegionAlias
from app.schemas.ai import Citation
from app.services import query_service

DEFAULT_PERIOD = query_service.DEFAULT_PERIOD_YEAR
MAX_ROWS = 500
MAX_REGIONS = 20
MAX_PERIODS = 5
MAX_INDICATORS = 10
MAX_RANK = 15
LOCAL_TZ = timezone(timedelta(hours=8))


class ToolError(Exception):
    """Structured tool failure returned to the agent instead of a traceback."""

    def __init__(self, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    def as_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "hint": self.hint}}


@dataclass
class ToolContext:
    session: AsyncSession
    citation_counter: int = 0
    calls: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)

    def next_citation_id(self) -> str:
        self.citation_counter += 1
        return f"c{self.citation_counter}"

    def record_call(self) -> None:
        self.calls += 1


def today_iso() -> str:
    return datetime.now(LOCAL_TZ).date().isoformat()


def _as_of(value: datetime | None) -> str:
    if value is None:
        return today_iso()
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ)
    return value.date().isoformat()


def _value(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _citation(
    ctx: ToolContext,
    *,
    indicator: Indicator | None,
    region: Region | None,
    indicator_code: str,
    indicator_name: str,
    region_code: str | None,
    region_name: str | None,
    region_level: str,
    period: int | str,
    data_as_of: str | None,
) -> Citation:
    citation_id = ctx.next_citation_id()
    return Citation(
        id=citation_id,
        citation_id=citation_id,
        indicator=indicator_name,
        indicator_name=indicator_name,
        indicator_id=indicator.id if indicator is not None else None,
        indicator_code=indicator_code,
        region=region_name,
        region_id=region.id if region is not None else None,
        region_code=region_code,
        region_name=region_name,
        region_level=region_level,
        period=str(period),
        source="data_values",
        data_as_of=data_as_of,
    )


async def resolve_entities(
    ctx: ToolContext,
    *,
    text: str = "",
    kind: str | None = None,
    level: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 10))
    regions: list[Region] = []
    indicators: list[Indicator] = []
    if kind in (None, "region"):
        stmt = select(Region).where(Region.enabled.is_(True))
        if level:
            stmt = stmt.where(Region.level == level)
        if text:
            alias_ids = select(RegionAlias.region_id).where(RegionAlias.alias.contains(text))
            stmt = stmt.where(
                or_(
                    Region.name.contains(text),
                    Region.code == text,
                    Region.id.in_(alias_ids),
                )
            )
        regions = list(
            (await ctx.session.execute(stmt.order_by(Region.sort_order, Region.id).limit(limit)))
            .scalars()
            .all()
        )
    if kind in (None, "indicator"):
        stmt = select(Indicator).where(Indicator.enabled.is_(True))
        if text:
            stmt = stmt.where(
                or_(Indicator.name.contains(text), Indicator.code.contains(text))
            )
        indicators = list(
            (await ctx.session.execute(stmt.order_by(Indicator.sort_order).limit(limit)))
            .scalars()
            .all()
        )
    return {
        "regions": [
            {
                "id": region.id,
                "code": region.code,
                "name": region.name,
                "level": region.level,
                "category": region.category,
            }
            for region in regions
        ],
        "indicators": [
            {
                "id": indicator.id,
                "code": indicator.code,
                "name": indicator.name,
                "unit": indicator.unit,
                "value_type": indicator.value_type,
                "precision": indicator.precision,
                "applicable_levels": indicator.applicable_levels,
            }
            for indicator in indicators
        ],
    }


async def describe_dataset(
    ctx: ToolContext,
    *,
    indicator_code: str | None = None,
    indicator_codes: list[str] | None = None,
    region_code: str | None = None,
    period: int | None = None,
) -> dict[str, Any]:
    codes = list(dict.fromkeys(indicator_codes or ([indicator_code] if indicator_code else [])))
    if not codes:
        raise ToolError("INVALID_ARGS", "indicator_code is required")
    if len(codes) > MAX_INDICATORS:
        raise ToolError("LIMIT_EXCEEDED", "too many indicators")
    indicators = list(
        (
            await ctx.session.execute(
                select(Indicator).where(Indicator.code.in_(codes)).order_by(Indicator.sort_order)
            )
        )
        .scalars()
        .all()
    )
    if not indicators:
        raise ToolError("NOT_FOUND", "indicator not found")
    output = []
    for indicator in indicators:
        period_stmt = (
            select(DataValue.period_year)
            .where(
                DataValue.indicator_id == indicator.id,
                DataValue.status == "published",
            )
            .distinct()
            .order_by(DataValue.period_year)
        )
        available = [int(value) for value in (await ctx.session.execute(period_stmt)).scalars()]
        coverage = None
        if region_code:
            region = await _resolve_region(ctx.session, region_code)
            count_stmt = (
                select(func.count())
                .select_from(DataValue)
                .where(
                    DataValue.indicator_id == indicator.id,
                    DataValue.region_id == region.id,
                    DataValue.status == "published",
                    DataValue.value_number.is_not(None),
                )
            )
            coverage = int((await ctx.session.execute(count_stmt)).scalar_one())
        output.append(
            {
                "code": indicator.code,
                "name": indicator.name,
                "unit": indicator.unit,
                "value_type": indicator.value_type,
                "precision": indicator.precision,
                "applicable_levels": indicator.applicable_levels,
                "available_periods": available,
                "coverage": coverage,
                "period": period,
                "region_code": region_code,
            }
        )
    return {"indicators": output}


async def _resolve_region(session: AsyncSession, code_or_name: str) -> Region:
    region = (
        await session.execute(
            select(Region).where(
                or_(Region.code == code_or_name, Region.name == code_or_name),
                Region.enabled.is_(True),
            )
        )
    ).scalars().first()
    if region is None:
        alias_target = (
            await session.execute(
                select(Region)
                .join(RegionAlias, RegionAlias.region_id == Region.id)
                .where(RegionAlias.alias == code_or_name)
            )
        ).scalars().first()
        region = alias_target
    if region is None:
        raise ToolError("NOT_FOUND", f"region not found: {code_or_name}")
    return region


async def query_observations(
    ctx: ToolContext,
    *,
    indicator_codes: list[str] | None = None,
    region_codes: list[str] | None = None,
    periods: list[int] | None = None,
) -> dict[str, Any]:
    indicator_codes = list(dict.fromkeys(indicator_codes or []))
    region_codes = list(dict.fromkeys(region_codes or []))
    periods = list(dict.fromkeys(periods or [DEFAULT_PERIOD]))
    if not indicator_codes or not region_codes:
        raise ToolError("INVALID_ARGS", "indicator_codes and region_codes are required")
    if len(indicator_codes) > MAX_INDICATORS:
        raise ToolError("LIMIT_EXCEEDED", "too many indicators")
    if len(region_codes) > MAX_REGIONS:
        raise ToolError("LIMIT_EXCEEDED", "too many regions")
    if len(periods) > MAX_PERIODS:
        raise ToolError("LIMIT_EXCEEDED", "too many periods")

    stmt = (
        select(DataValue, Region, Indicator)
        .join(Region, DataValue.region_id == Region.id)
        .join(Indicator, DataValue.indicator_id == Indicator.id)
        .where(
            DataValue.status == "published",
            DataValue.period_year.in_(periods),
            Region.code.in_(region_codes),
            Indicator.code.in_(indicator_codes),
        )
        .order_by(DataValue.indicator_id, Region.sort_order, Region.id)
    )
    records = (await ctx.session.execute(stmt)).all()
    if not records:
        raise ToolError("NO_DATA", "no observations for the requested combination")
    if len(records) > MAX_ROWS:
        raise ToolError("LIMIT_EXCEEDED", "result exceeds 500 rows")

    rows: list[dict[str, Any]] = []
    citations: list[Citation] = []
    for value, region, indicator in records:
        citation = _citation(
            ctx,
            indicator=indicator,
            region=region,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            region_code=region.code,
            region_name=region.name,
            region_level=region.level,
            period=value.period_year,
            data_as_of=_as_of(value.updated_at),
        )
        citations.append(citation)
        rows.append(
            {
                "region_id": region.id,
                "region_code": region.code,
                "region_name": region.name,
                "region_level": region.level,
                "indicator_id": indicator.id,
                "indicator_code": indicator.code,
                "indicator_name": indicator.name,
                "unit": indicator.unit,
                "period": value.period_year,
                "value": _value(value.value_number),
                "value_text": value.value_text,
                "quality_status": value.quality_status,
                "citation_id": citation.id,
            }
        )
    ctx.rows.extend(rows)
    return {"rows": rows, "citations": [c.model_dump(mode="json") for c in citations]}


async def rank_regions(
    ctx: ToolContext,
    *,
    indicator_code: str,
    period: int = DEFAULT_PERIOD,
    level: str = "town",
    order: str = "desc",
    limit: int = 10,
    include_development_zones: bool = False,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), MAX_RANK))
    items, indicator = await query_service.rank_data_values(
        ctx.session,
        indicator_code=indicator_code,
        period_year=int(period),
        level=level,
        order=order,
        limit=limit,
        include_development_zones=bool(include_development_zones),
    )
    if not items:
        raise ToolError("NO_DATA", "no ranked values for the requested period")
    citation = _citation(
        ctx,
        indicator=indicator,
        region=None,
        indicator_code=indicator.code,
        indicator_name=indicator.name,
        region_code=None,
        region_name=None,
        region_level=level,
        period=period,
        data_as_of=today_iso(),
    )
    rows = [
        {
            "rank": item.rank,
            "region_id": item.region_id,
            "region_code": item.region_code,
            "region_name": item.region_name,
            "indicator_code": indicator.code,
            "value": _value(item.value_number),
            "unit": item.unit,
            "citation_id": citation.id,
        }
        for item in items
    ]
    ctx.rows.extend(rows)
    return {
        "rows": rows,
        "indicator": {
            "code": indicator.code,
            "name": indicator.name,
            "unit": indicator.unit,
            "precision": indicator.precision,
        },
        "citations": [citation.model_dump(mode="json")],
    }


async def compare_regions(
    ctx: ToolContext,
    *,
    indicator_code: str,
    region_codes: list[str],
    period: int = DEFAULT_PERIOD,
) -> dict[str, Any]:
    region_codes = list(dict.fromkeys(region_codes or []))
    if len(region_codes) < 2 or len(region_codes) > 6:
        raise ToolError("INVALID_ARGS", "compare requires 2-6 regions")
    items, indicator = await query_service.compare_data_values(
        ctx.session,
        indicator_code=indicator_code,
        region_codes=",".join(region_codes),
        period_year=int(period),
    )
    if not items:
        raise ToolError("NO_DATA", "no comparison values for the requested period")

    regions = {
        region.code: region
        for region in (
            await ctx.session.execute(select(Region).where(Region.code.in_(region_codes)))
        )
        .scalars()
        .all()
    }
    rows: list[dict[str, Any]] = []
    citations: list[Citation] = []
    for item in items:
        region = regions.get(item.region_code)
        citation = _citation(
            ctx,
            indicator=indicator,
            region=region,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            region_code=item.region_code,
            region_name=item.region_name,
            region_level=region.level if region is not None else "town",
            period=period,
            data_as_of=today_iso(),
        )
        citations.append(citation)
        rows.append(
            {
                "region_id": item.region_id,
                "region_code": item.region_code,
                "region_name": item.region_name,
                "indicator_code": indicator.code,
                "value": _value(item.value_number),
                "quality_status": item.quality_status,
                "unit": item.unit,
                "diff_from_first": item.diff_from_first,
                "diff_pct_from_first": item.diff_pct_from_first,
                "citation_id": citation.id,
            }
        )
    ctx.rows.extend(rows)
    return {
        "rows": rows,
        "indicator": {
            "code": indicator.code,
            "name": indicator.name,
            "unit": indicator.unit,
            "precision": indicator.precision,
        },
        "citations": [c.model_dump(mode="json") for c in citations],
    }


async def trend_values(
    ctx: ToolContext,
    *,
    indicator_code: str,
    region_codes: list[str],
    periods: list[int] | None = None,
) -> dict[str, Any]:
    region_codes = list(dict.fromkeys(region_codes or []))
    if not region_codes or len(region_codes) > 5:
        raise ToolError("INVALID_ARGS", "trend requires 1-5 regions")
    indicator = (
        await ctx.session.execute(select(Indicator).where(Indicator.code == indicator_code))
    ).scalars().first()
    if indicator is None:
        raise ToolError("NOT_FOUND", "indicator not found")
    if periods:
        period_values = sorted({int(period) for period in periods})
    else:
        period_values = [
            int(value)
            for value in (
                await ctx.session.execute(
                    select(DataValue.period_year)
                    .where(
                        DataValue.indicator_id == indicator.id,
                        DataValue.status == "published",
                    )
                    .distinct()
                    .order_by(DataValue.period_year)
                )
            ).scalars()
        ]
    if len(period_values) < 2:
        raise ToolError(
            "NOT_ENOUGH_PERIODS",
            "trend requires at least two periods",
            "Demo v0 only publishes one period",
        )
    payload = await query_observations(
        ctx,
        indicator_codes=[indicator_code],
        region_codes=region_codes,
        periods=period_values[-MAX_PERIODS:],
    )
    series: dict[str, list[dict[str, Any]]] = {code: [] for code in region_codes}
    for row in payload["rows"]:
        series.setdefault(row["region_code"], []).append(
            {"period": row["period"], "value": row["value"]}
        )
    return {
        "indicator": {"code": indicator.code, "name": indicator.name, "unit": indicator.unit},
        "series": [{"region_code": code, "points": series[code]} for code in region_codes],
        "citations": payload["citations"],
    }


async def composition(
    ctx: ToolContext,
    *,
    indicator_code: str,
    period: int = DEFAULT_PERIOD,
    level: str = "town",
    parent_code: str | None = None,
) -> dict[str, Any]:
    payload = await rank_regions(
        ctx,
        indicator_code=indicator_code,
        period=period,
        level=level,
        order="desc",
        limit=MAX_RANK,
        include_development_zones=False,
    )
    region_stmt = select(func.count()).select_from(Region).where(
        Region.level == level,
        Region.enabled.is_(True),
    )
    if level == "town":
        region_stmt = region_stmt.where(Region.category == "administrative")
    expected = int((await ctx.session.execute(region_stmt)).scalar_one())
    rows = payload["rows"]
    if parent_code:
        parent = await _resolve_region(ctx.session, parent_code)
        filtered: list[dict[str, Any]] = []
        for row in rows:
            region = await ctx.session.get(Region, row["region_id"])
            if region is not None and region.parent_id == parent.id:
                filtered.append(row)
        rows = filtered
    if len(rows) < expected:
        raise ToolError(
            "PARTIAL_COVERAGE",
            "not every region in the level has a value",
            "ratio cannot be computed",
        )
    total = sum(float(row["value"]) for row in rows if row["value"] is not None)
    if total <= 0:
        raise ToolError("PARTIAL_COVERAGE", "total is not positive")
    parts = [
        {
            **row,
            "share_pct": round(float(row["value"]) / total * 100, 2),
        }
        for row in rows
    ]
    return {
        "indicator": payload["indicator"],
        "total": total,
        "parts": parts,
        "citations": payload["citations"],
    }


async def get_region_profile(
    ctx: ToolContext,
    *,
    region_code: str,
    period: int | None = None,
) -> dict[str, Any]:
    region = await _resolve_region(ctx.session, region_code)
    profile = await query_service.get_region_profile(ctx.session, region.id)
    citations: list[Citation] = []
    metrics: list[dict[str, Any]] = []
    for metric in profile.metrics[:6]:
        indicator = await ctx.session.get(Indicator, metric.indicator_id)
        citation = _citation(
            ctx,
            indicator=indicator,
            region=region,
            indicator_code=metric.code,
            indicator_name=metric.name,
            region_code=region.code,
            region_name=region.name,
            region_level=region.level,
            period=period or metric.period_year,
            data_as_of=_as_of(profile.data_as_of),
        )
        if metric.value_number is not None:
            citations.append(citation)
        metrics.append(
            {
                "indicator_id": metric.indicator_id,
                "indicator_code": metric.code,
                "label": metric.name,
                "value": _value(metric.value_number),
                "unit": metric.unit,
                "period": period or metric.period_year,
                "quality_status": metric.quality_status,
                "citation_id": citation.id if metric.value_number is not None else None,
            }
        )
        ctx.rows.append(
            {
                "region_code": region.code,
                "region_name": region.name,
                "indicator_code": metric.code,
                "period": period or metric.period_year,
                "value": _value(metric.value_number),
            }
        )
    return {
        "region": {
            "id": region.id,
            "code": region.code,
            "name": region.name,
            "level": region.level,
        },
        "intro": profile.intro,
        "feature": profile.feature,
        "metrics": metrics,
        "data_as_of": _as_of(profile.data_as_of),
        "citations": [c.model_dump(mode="json") for c in citations],
    }


async def compute_metric(
    ctx: ToolContext,
    *,
    formula: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    def number(key: str) -> float:
        value = inputs.get(key)
        if value is None or isinstance(value, bool):
            raise ToolError("INVALID_ARGS", f"input {key} must be numeric")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ToolError("INVALID_ARGS", f"input {key} must be numeric") from exc

    if formula == "diff":
        value = number("first") - number("second")
        explanation = "first - second"
    elif formula == "share":
        total = number("total")
        if total == 0:
            raise ToolError("INVALID_ARGS", "total must not be zero")
        value = number("part") / total * 100
        explanation = "part / total * 100"
    elif formula == "per_capita":
        population = number("population")
        if population == 0:
            raise ToolError("INVALID_ARGS", "population must not be zero")
        value = number("value") / population
        explanation = "value / population"
    elif formula == "growth":
        base = number("base")
        if base == 0:
            raise ToolError("INVALID_ARGS", "base must not be zero")
        value = (number("current") - base) / base * 100
        explanation = "(current - base) / base * 100"
    else:
        raise ToolError("INVALID_ARGS", "unsupported formula")
    return {"value": round(value, 4), "formula": formula, "explanation": explanation}


async def correlation(
    ctx: ToolContext,
    *,
    indicator_x: str,
    indicator_y: str,
    level: str = "town",
    period: int = DEFAULT_PERIOD,
) -> dict[str, Any]:
    raise ToolError(
        "TOOL_DISABLED",
        "correlation is disabled in Demo v0",
        "relationship analysis arrives in M1",
    )


ToolHandler = Callable[..., Awaitable[dict[str, Any]]]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "resolve_entities": resolve_entities,
    "describe_dataset": describe_dataset,
    "query_observations": query_observations,
    "rank_regions": rank_regions,
    "compare_regions": compare_regions,
    "trend_values": trend_values,
    "composition": composition,
    "get_region_profile": get_region_profile,
    "compute_metric": compute_metric,
    "correlation": correlation,
}


async def execute_tool(ctx: ToolContext, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ToolError("INVALID_ARGS", f"unknown tool: {name}")
    if not isinstance(args, dict):
        raise ToolError("INVALID_ARGS", "tool arguments must be an object")
    ctx.record_call()
    try:
        return await handler(ctx, **args)
    except TypeError as exc:
        raise ToolError("INVALID_ARGS", f"invalid arguments for {name}: {exc}") from exc


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "resolve_entities",
            "description": "Resolve region or indicator names mentioned in the question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "kind": {"type": "string", "enum": ["region", "indicator"]},
                    "level": {"type": "string", "enum": ["district", "town", "village"]},
                    "limit": {"type": "integer"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_dataset",
            "description": "Return indicator metadata, unit, available periods, and coverage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_code": {"type": "string"},
                    "indicator_codes": {"type": "array", "items": {"type": "string"}},
                    "region_code": {"type": "string"},
                    "period": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_observations",
            "description": "Return published observations with citation ids.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_codes": {"type": "array", "items": {"type": "string"}},
                    "region_codes": {"type": "array", "items": {"type": "string"}},
                    "periods": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["indicator_codes", "region_codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_regions",
            "description": "Rank regions by one numeric indicator for a period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_code": {"type": "string"},
                    "period": {"type": "integer"},
                    "level": {"type": "string", "enum": ["district", "town", "village"]},
                    "order": {"type": "string", "enum": ["asc", "desc"]},
                    "limit": {"type": "integer"},
                    "include_development_zones": {"type": "boolean"},
                },
                "required": ["indicator_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_regions",
            "description": "Compare 2-6 regions for one indicator and period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_code": {"type": "string"},
                    "region_codes": {"type": "array", "items": {"type": "string"}},
                    "period": {"type": "integer"},
                },
                "required": ["indicator_code", "region_codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trend_values",
            "description": "Return at least two periods for one indicator.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_code": {"type": "string"},
                    "region_codes": {"type": "array", "items": {"type": "string"}},
                    "periods": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["indicator_code", "region_codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composition",
            "description": "Return parts, total, and share for a complete parent level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_code": {"type": "string"},
                    "period": {"type": "integer"},
                    "level": {"type": "string", "enum": ["district", "town", "village"]},
                    "parent_code": {"type": "string"},
                },
                "required": ["indicator_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_region_profile",
            "description": "Return one region profile: narrative text, key metrics, citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region_code": {"type": "string"},
                    "period": {"type": "integer"},
                },
                "required": ["region_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_metric",
            "description": "Apply a whitelisted formula (share, per_capita, growth, diff).",
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "enum": ["share", "per_capita", "growth", "diff"],
                    },
                    "inputs": {"type": "object"},
                },
                "required": ["formula", "inputs"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correlation",
            "description": "Disabled in Demo v0; returns TOOL_DISABLED.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_x": {"type": "string"},
                    "indicator_y": {"type": "string"},
                    "level": {"type": "string"},
                    "period": {"type": "integer"},
                },
            },
        },
    },
]
