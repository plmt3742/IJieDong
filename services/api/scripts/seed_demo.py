"""Deterministic synthetic Demo v0 seed for i揭东.

Populates the B01 schema with the full 2025 demo shape:

* 15 indicators (2 text + 13 numeric)
* 227 regions (1 district + 15 town-level nodes + 211 villages)
* 1608 applicable data values, including a deterministic missing subset
* 1 region alias (玉窖镇 -> 玉滘镇), 1 demo data source, 1 demo import job

Values are derived from SHA-256 of ``(seed, region_code, indicator_code)`` so
the output is reproducible. All text is explicitly marked as synthetic
(``演示文本``) and must never be presented as real statistics.

Usage (from ``services/api``)::

    python scripts/seed_demo.py                       # seed configured DB
    python scripts/seed_demo.py --check               # counts only, no writes
    python scripts/seed_demo.py --database-url sqlite:///./data/demo.db
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

_API_ROOT = Path(__file__).resolve().parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

import app.models  # noqa: E402,F401  (registers every table on Base.metadata)
from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine_and_sessionmaker  # noqa: E402
from app.models import (  # noqa: E402
    DataSource,
    DataValue,
    ImportJob,
    Indicator,
    Region,
    RegionAlias,
)

SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = SCRIPT_DIR / "fixtures" / "regions_2025.json"

DEFAULT_SEED = 20261110
PERIOD_YEAR = 2025
PERIOD_TYPE = "year"
DEMO_SOURCE_NAME = "演示数据（合成）"
DEMO_SOURCE_OWNER = "seed_demo"
DEMO_IMPORT_FILENAME = "seed_demo.py"
ALIAS_NAME = "玉窖镇"
ALIAS_TARGET_NAME = "玉滘镇"

EXPECTED_REGIONS = 227
EXPECTED_INDICATORS = 15
EXPECTED_DATA_VALUES = 1608
MISSING_RATE_PERCENT = 3

EXPECTED_APPLICABILITY = {
    "district": 15,
    "administrative_town": 104,
    "development_zone": 12,
    "village": 1477,
}

ALL_LEVELS = ["district", "town", "village"]
ADMINISTRATIVE = ["administrative"]

INDICATORS: list[dict[str, Any]] = [
    {
        "code": "region_intro",
        "name": "地区简介",
        "unit": "文本",
        "value_type": "long_text",
        "category": "文本",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 0,
        "max_length": 150,
        "direction": "neutral",
        "sort_order": 1,
        "description": "区域简介文本，最多 150 字；演示值为确定性合成内容。",
    },
    {
        "code": "region_feature",
        "name": "地区特色",
        "unit": "文本",
        "value_type": "long_text",
        "category": "文本",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 0,
        "max_length": 300,
        "direction": "neutral",
        "sort_order": 2,
        "description": "区域特色文本，最多 300 字；演示值为确定性合成内容。",
    },
    {
        "code": "area",
        "name": "区域面积",
        "unit": "平方公里",
        "value_type": "decimal",
        "category": "基础",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 3,
        "description": "区域面积，单位平方公里；演示值为确定性合成值，不自动加总。",
    },
    {
        "code": "admin_village_count",
        "name": "行政村数量",
        "unit": "个",
        "value_type": "integer",
        "category": "基础",
        "applicable_levels": ["district", "town"],
        "applicable_region_categories": ADMINISTRATIVE,
        "aggregation": "none",
        "precision": 0,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 4,
        "description": "行政村数量，仅区与 13 个行政镇街适用；开发区/生态城不适用。",
    },
    {
        "code": "population_resident",
        "name": "常住人口",
        "unit": "人",
        "value_type": "integer",
        "category": "人口",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 0,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 5,
        "description": "常住人口，单位人；空值表示缺失，不以 0 代替。",
    },
    {
        "code": "population_household",
        "name": "户籍人口数",
        "unit": "人",
        "value_type": "integer",
        "category": "人口",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 0,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 6,
        "description": "户籍人口数，单位人；合成值按常住人口的 0.6 至 0.9 生成。",
    },
    {
        "code": "farmland_area",
        "name": "耕地面积",
        "unit": "亩",
        "value_type": "decimal",
        "category": "资源",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": ADMINISTRATIVE,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 7,
        "description": "耕地面积，单位亩；开发区/生态城不适用。",
    },
    {
        "code": "forest_area",
        "name": "林地面积",
        "unit": "亩",
        "value_type": "decimal",
        "category": "资源",
        "applicable_levels": ALL_LEVELS,
        "applicable_region_categories": ADMINISTRATIVE,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 8,
        "description": "林地面积，单位亩；开发区/生态城不适用。",
    },
    {
        "code": "gdp",
        "name": "地区生产总值",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district", "town"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 9,
        "description": "地区生产总值，单位亿元；模板仅区与 2 个开发区/生态城有值。",
    },
    {
        "code": "budget_revenue",
        "name": "地方一般公共预算收入",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 10,
        "description": "地方一般公共预算收入，单位亿元；仅区级适用。",
    },
    {
        "code": "budget_expenditure",
        "name": "地方一般公共预算支出",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 11,
        "description": "地方一般公共预算支出，单位亿元；仅区级适用。",
    },
    {
        "code": "import_export_total",
        "name": "进出口总额",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 12,
        "description": "进出口总额，单位亿元；仅区级适用。",
    },
    {
        "code": "fixed_asset_investment",
        "name": "固定资产投资",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 13,
        "description": "固定资产投资，单位亿元；仅区级适用。",
    },
    {
        "code": "industrial_investment",
        "name": "工业投资额",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 14,
        "description": "工业投资额，单位亿元；仅区级适用。",
    },
    {
        "code": "retail_total",
        "name": "社会消费品零售总额",
        "unit": "亿元",
        "value_type": "currency",
        "category": "经济",
        "applicable_levels": ["district"],
        "applicable_region_categories": None,
        "aggregation": "none",
        "precision": 2,
        "max_length": None,
        "direction": "neutral",
        "sort_order": 15,
        "description": "社会消费品零售总额，单位亿元；仅区级适用。",
    },
]

INDICATOR_BY_CODE = {indicator["code"]: indicator for indicator in INDICATORS}

DISTRICT_RANGES: dict[str, tuple[float, float]] = {
    "area": (350.0, 450.0),
    "population_resident": (150_000.0, 200_000.0),
    "farmland_area": (220_000.0, 380_000.0),
    "forest_area": (120_000.0, 280_000.0),
    "gdp": (250.0, 300.0),
    "budget_revenue": (20.0, 60.0),
    "budget_expenditure": (40.0, 100.0),
    "import_export_total": (30.0, 120.0),
    "fixed_asset_investment": (80.0, 200.0),
    "industrial_investment": (30.0, 90.0),
    "retail_total": (100.0, 250.0),
}

DEVELOPMENT_ZONE_RANGES: dict[str, tuple[float, float]] = {
    "area": (10.0, 40.0),
    "population_resident": (3_000.0, 20_000.0),
    "gdp": (50.0, 150.0),
}

TOWN_RANGES: dict[str, tuple[float, float]] = {
    "area": (25.0, 120.0),
    "population_resident": (15_000.0, 80_000.0),
    "farmland_area": (10_000.0, 60_000.0),
    "forest_area": (6_000.0, 40_000.0),
}

VILLAGE_RANGES: dict[str, tuple[float, float]] = {
    "area": (5.0, 20.0),
    "population_resident": (1_000.0, 12_000.0),
    "farmland_area": (500.0, 8_000.0),
    "forest_area": (200.0, 6_000.0),
}

INTEGER_INDICATORS = {"admin_village_count", "population_resident", "population_household"}


def _to_async_url(database_url: str) -> str:
    """Convert a sync SQLAlchemy URL to its async driver equivalent."""
    if database_url.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + database_url[len("sqlite:///") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    return database_url


def _load_fixture() -> list[dict[str, Any]]:
    if not FIXTURE_PATH.exists():
        raise RuntimeError(
            f"region fixture not found at {FIXTURE_PATH}; run scripts/build_region_fixture.py"
        )
    regions = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or len(regions) != EXPECTED_REGIONS:
        raise RuntimeError(
            f"region fixture must contain {EXPECTED_REGIONS} entries, got {len(regions)}"
        )
    return regions


def _digest(seed: int, region_code: str, indicator_code: str) -> bytes:
    payload = f"{seed}:{region_code}:{indicator_code}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def _fraction(seed: int, region_code: str, indicator_code: str) -> float:
    digest = _digest(seed, region_code, indicator_code)
    return int.from_bytes(digest[:8], "big") / float(2**64)


def _is_missing(seed: int, region: dict[str, Any], indicator_code: str) -> bool:
    if region["level"] == "district":
        return False
    digest = _digest(seed, region["code"], indicator_code)
    return digest[8] % 100 < MISSING_RATE_PERCENT


def _applies(region: dict[str, Any], indicator: dict[str, Any]) -> bool:
    if region["level"] not in indicator["applicable_levels"]:
        return False
    categories = indicator.get("applicable_region_categories")
    if categories and region["category"] not in categories:
        return False
    if indicator["code"] == "gdp":
        # Only the district and the two development zones carry GDP in the template.
        return region["level"] == "district" or region["category"] == "development_zone"
    return True


def _applicability_group(region: dict[str, Any]) -> str:
    if region["level"] == "district":
        return "district"
    if region["level"] == "village":
        return "village"
    if region["category"] == "development_zone":
        return "development_zone"
    return "administrative_town"


def _applicability_counts(regions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {group: 0 for group in EXPECTED_APPLICABILITY}
    for region in regions:
        for indicator in INDICATORS:
            if _applies(region, indicator):
                counts[_applicability_group(region)] += 1
    return counts


def _range_for(indicator_code: str, region: dict[str, Any]) -> tuple[float, float]:
    if region["level"] == "district":
        return DISTRICT_RANGES[indicator_code]
    if region["category"] == "development_zone":
        return DEVELOPMENT_ZONE_RANGES[indicator_code]
    if region["level"] == "town":
        return TOWN_RANGES[indicator_code]
    return VILLAGE_RANGES[indicator_code]


def _int_value(seed: int, region: dict[str, Any], indicator_code: str) -> int:
    low, high = _range_for(indicator_code, region)
    span = int(high) - int(low) + 1
    return int(low) + int(_fraction(seed, region["code"], indicator_code) * span)


def _decimal_value(seed: int, region: dict[str, Any], indicator_code: str) -> Decimal:
    low, high = _range_for(indicator_code, region)
    value = low + (high - low) * _fraction(seed, region["code"], indicator_code)
    return Decimal(f"{value:.2f}")


def _numeric_value(
    seed: int,
    region: dict[str, Any],
    indicator_code: str,
    village_counts: dict[str, int],
) -> Decimal:
    if indicator_code == "admin_village_count":
        if region["level"] == "district":
            return Decimal(sum(village_counts.values()))
        return Decimal(village_counts.get(region["code"], 0))
    if indicator_code == "population_household":
        resident = _int_value(seed, region, "population_resident")
        ratio = 0.6 + 0.3 * _fraction(seed, region["code"], indicator_code)
        return Decimal(int(round(resident * ratio)))
    if indicator_code in INTEGER_INDICATORS:
        return Decimal(_int_value(seed, region, indicator_code))
    return _decimal_value(seed, region, indicator_code)


LEVEL_LABELS = {"district": "区级", "town": "镇街级", "village": "村居级"}


def _text_value(seed: int, region: dict[str, Any], indicator_code: str) -> str:
    marker = _digest(seed, region["code"], indicator_code)[:4].hex()
    level_label = LEVEL_LABELS[region["level"]]
    if indicator_code == "region_intro":
        return (
            f"演示文本：{region['name']}（{level_label}合成区域，标记 {marker}）"
            "用于验证区域简介的排版与换行，不构成任何真实统计或结论。"
        )
    return (
        f"演示文本：{region['name']}（{level_label}合成区域，标记 {marker}）"
        "的特色条目为确定性生成，仅用于演示产业、文化与生态等展示位，"
        "不构成任何真实统计或结论。"
    )


def _build_planned_values(
    regions: list[dict[str, Any]],
    seed: int,
) -> list[dict[str, Any]]:
    """Build the full 1608-row value plan without touching the database."""
    village_counts: dict[str, int] = {}
    for region in regions:
        parent_code = region["parent_code"]
        if region["level"] == "village" and parent_code:
            village_counts[parent_code] = village_counts.get(parent_code, 0) + 1

    planned: list[dict[str, Any]] = []
    for region in regions:
        for indicator in INDICATORS:
            if not _applies(region, indicator):
                continue
            code = indicator["code"]
            if indicator["value_type"] == "long_text":
                value_text = _text_value(seed, region, code)
                max_length = indicator["max_length"]
                if max_length is not None and len(value_text) > max_length:
                    raise RuntimeError(
                        f"generated text for {region['code']}/{code} exceeds {max_length}"
                    )
                planned.append(
                    {
                        "region_code": region["code"],
                        "indicator_code": code,
                        "value_number": None,
                        "value_text": value_text,
                        "quality_status": "verified",
                    }
                )
                continue

            missing = _is_missing(seed, region, code)
            planned.append(
                {
                    "region_code": region["code"],
                    "indicator_code": code,
                    "value_number": (
                        None if missing else _numeric_value(seed, region, code, village_counts)
                    ),
                    "value_text": None,
                    "quality_status": "missing" if missing else "verified",
                }
            )

    if not any(item["quality_status"] == "missing" for item in planned):
        # Deterministic safety net: never ship a demo without a missing-value case.
        for item in planned:
            if item["value_number"] is not None:
                item["value_number"] = None
                item["quality_status"] = "missing"
                break

    applicability = _applicability_counts(regions)
    if applicability != EXPECTED_APPLICABILITY:
        raise RuntimeError(
            f"applicability mismatch: {applicability} != {EXPECTED_APPLICABILITY}"
        )
    if len(planned) != EXPECTED_DATA_VALUES:
        raise RuntimeError(
            f"planned data values {len(planned)} != {EXPECTED_DATA_VALUES}"
        )
    return planned


async def _scalar_count(session: AsyncSession, statement: Any) -> int:
    return int((await session.execute(statement)).scalar_one())


def _count_statement(model: Any) -> Any:
    return select(func.count()).select_from(model)


async def _check_summary(
    session: AsyncSession,
    regions: list[dict[str, Any]],
    planned: list[dict[str, Any]],
) -> dict[str, Any]:
    existing: dict[str, int] | None
    try:
        existing = {
            "regions": await _scalar_count(session, _count_statement(Region)),
            "indicators": await _scalar_count(session, _count_statement(Indicator)),
            "data_values": await _scalar_count(session, _count_statement(DataValue)),
            "region_aliases": await _scalar_count(session, _count_statement(RegionAlias)),
            "data_sources": await _scalar_count(session, _count_statement(DataSource)),
            "import_jobs": await _scalar_count(session, _count_statement(ImportJob)),
        }
    except SQLAlchemyError:
        await session.rollback()
        existing = None

    text_values = sum(1 for item in planned if item["value_text"] is not None)
    missing_values = sum(1 for item in planned if item["quality_status"] == "missing")
    return {
        "mode": "check",
        "fixture_regions": len(regions),
        "indicators": len(INDICATORS),
        "expected_data_values": len(planned),
        "text_values": text_values,
        "missing_values": missing_values,
        "applicability": _applicability_counts(regions),
        "existing": existing,
    }


async def _apply_seed(
    session: AsyncSession,
    regions: list[dict[str, Any]],
    planned: list[dict[str, Any]],
) -> dict[str, Any]:
    needed_codes = {region["code"] for region in regions}
    existing_regions = {
        region.code: region
        for region in (await session.execute(select(Region))).scalars()
        if region.code in needed_codes
    }

    region_objects: dict[str, Region] = {}
    for node in regions:
        region = existing_regions.get(node["code"])
        if region is None:
            region = Region(code=node["code"])
            session.add(region)
        region.name = node["name"]
        region.level = node["level"]
        region.category = node["category"]
        region.parent_id = (
            region_objects[node["parent_code"]].id if node["parent_code"] else None
        )
        region.sort_order = node["sort_order"]
        region.external_code = node["external_code"]
        region.enabled = node["enabled"]
        await session.flush()
        region_objects[node["code"]] = region

    existing_indicators = {
        indicator.code: indicator
        for indicator in (await session.execute(select(Indicator))).scalars()
    }
    indicator_objects: dict[str, Indicator] = {}
    for spec in INDICATORS:
        indicator = existing_indicators.get(spec["code"])
        if indicator is None:
            indicator = Indicator(code=spec["code"])
            session.add(indicator)
        indicator.name = spec["name"]
        indicator.unit = spec["unit"]
        indicator.value_type = spec["value_type"]
        indicator.category = spec["category"]
        indicator.applicable_levels = list(spec["applicable_levels"])
        indicator.applicable_region_categories = spec["applicable_region_categories"]
        indicator.aggregation = spec["aggregation"]
        indicator.precision = spec["precision"]
        indicator.max_length = spec["max_length"]
        indicator.direction = spec["direction"]
        indicator.description = spec["description"]
        indicator.sort_order = spec["sort_order"]
        indicator.enabled = True
        indicator.status = "active"
        indicator.version = 1
        await session.flush()
        indicator_objects[spec["code"]] = indicator

    alias_target = next(
        region
        for region in region_objects.values()
        if region.level == "town" and region.name == ALIAS_TARGET_NAME
    )
    alias = (
        await session.execute(
            select(RegionAlias).where(
                RegionAlias.region_id == alias_target.id,
                RegionAlias.alias == ALIAS_NAME,
            )
        )
    ).scalars().first()
    if alias is None:
        alias = RegionAlias(region_id=alias_target.id, alias=ALIAS_NAME)
        session.add(alias)
    alias.source = "seed_demo"

    source = (
        await session.execute(
            select(DataSource)
            .where(
                DataSource.name == DEMO_SOURCE_NAME,
                DataSource.source_type == "demo",
            )
            .order_by(DataSource.id)
        )
    ).scalars().first()
    if source is None:
        source = DataSource(
            name=DEMO_SOURCE_NAME,
            source_type="demo",
            owner=DEMO_SOURCE_OWNER,
        )
        session.add(source)
    source.owner = DEMO_SOURCE_OWNER
    source.description = (
        "确定性合成演示数据，由 scripts/seed_demo.py 生成，不代表真实统计。"
    )
    await session.flush()

    import_job = (
        await session.execute(
            select(ImportJob)
            .where(
                ImportJob.filename == DEMO_IMPORT_FILENAME,
                ImportJob.job_type == "manual",
            )
            .order_by(ImportJob.id)
        )
    ).scalars().first()
    if import_job is None:
        import_job = ImportJob(
            filename=DEMO_IMPORT_FILENAME,
            job_type="manual",
        )
        session.add(import_job)
    total_rows = len(planned)
    import_job.status = "success"
    import_job.mode = "atomic"
    import_job.total_rows = total_rows
    import_job.success_rows = total_rows
    import_job.error_rows = 0
    import_job.errors = None
    import_job.error_report_path = None
    import_job.finished_at = datetime.now(timezone.utc)
    await session.flush()

    existing_values = {
        (value.region_id, value.indicator_id): value
        for value in (
            await session.execute(
                select(DataValue).where(
                    DataValue.period_year == PERIOD_YEAR,
                    DataValue.period_type == PERIOD_TYPE,
                    DataValue.dimension_hash == "",
                )
            )
        ).scalars()
    }

    text_values = 0
    missing_values = 0
    for item in planned:
        region_id = region_objects[item["region_code"]].id
        indicator_id = indicator_objects[item["indicator_code"]].id
        value = existing_values.get((region_id, indicator_id))
        if value is None:
            value = DataValue(
                region_id=region_id,
                indicator_id=indicator_id,
                period_year=PERIOD_YEAR,
                period_type=PERIOD_TYPE,
                dimension_hash="",
            )
            session.add(value)
            existing_values[(region_id, indicator_id)] = value
        value.value_number = item["value_number"]
        value.value_text = item["value_text"]
        value.value_json = None
        value.quality_status = item["quality_status"]
        value.source_id = source.id
        value.import_job_id = import_job.id
        value.dimensions = None
        value.dimension_hash = ""
        value.version = 1
        value.status = "published"
        value.updated_by = None
        if item["value_text"] is not None:
            text_values += 1
        if item["quality_status"] == "missing":
            missing_values += 1

    await session.flush()

    return {
        "mode": "seed",
        "seed": None,  # filled by caller
        "regions": len(regions),
        "indicators": len(INDICATORS),
        "data_values": len(planned),
        "text_values": text_values,
        "missing_values": missing_values,
        "aliases": 1,
        "source": DEMO_SOURCE_NAME,
        "import_job": DEMO_IMPORT_FILENAME,
        "applicability": _applicability_counts(regions),
    }


async def seed_demo(
    database_url: str,
    *,
    seed: int = DEFAULT_SEED,
    check: bool = False,
) -> dict[str, Any]:
    """Seed (or inspect) the deterministic Demo v0 dataset.

    ``database_url`` may be a sync or async SQLAlchemy URL. When ``check`` is
    true the function only reads counts and never writes.
    """
    regions = _load_fixture()
    planned = _build_planned_values(regions, seed)

    engine, sessionmaker = create_engine_and_sessionmaker(_to_async_url(database_url))
    try:
        async with sessionmaker() as session:
            if check:
                return await _check_summary(session, regions, planned)
            summary = await _apply_seed(session, regions, planned)
            await session.commit()
            summary["seed"] = seed
            return summary
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic Demo v0 data.")
    parser.add_argument(
        "--database-url",
        help="SQLAlchemy database URL (defaults to the configured DATABASE_URL).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print expected/existing counts without writing.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic seed used for value generation (default: {DEFAULT_SEED}).",
    )
    args = parser.parse_args(argv)

    database_url = args.database_url or get_settings().database_url
    summary = asyncio.run(
        seed_demo(database_url, seed=args.seed, check=args.check)
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
