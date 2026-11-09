"""Tests for the deterministic Demo v0 seed (B02).

The seed function is async, so tests call it with ``asyncio.run``; assertions
use a synchronous SQLAlchemy session against the same temporary SQLite file.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import and_, create_engine, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    DataSource,
    DataValue,
    ImportJob,
    Indicator,
    Region,
    RegionAlias,
)
from scripts.seed_demo import seed_demo

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = API_ROOT / "alembic.ini"
ALEMBIC_SCRIPTS = API_ROOT / "alembic"

EXPECTED_APPLICABILITY = {
    "district": 15,
    "administrative_town": 104,
    "development_zone": 12,
    "village": 1477,
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@contextmanager
def _session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _migrate(database_url: str) -> None:
    command.upgrade(_alembic_config(database_url), "head")


def _count(session: Session, model: Any) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


def _data_value_count(
    session: Session,
    *,
    level: str | None = None,
    category: str | None = None,
    indicator_code: str | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(DataValue)
        .join(Region, DataValue.region_id == Region.id)
        .join(Indicator, DataValue.indicator_id == Indicator.id)
    )
    if level is not None:
        statement = statement.where(Region.level == level)
    if category is not None:
        statement = statement.where(Region.category == category)
    if indicator_code is not None:
        statement = statement.where(Indicator.code == indicator_code)
    return int(session.execute(statement).scalar_one())


@pytest.fixture()
def seeded_database_url(tmp_path: Path) -> str:
    database_url = f"sqlite:///{(tmp_path / 'seed.db').as_posix()}"
    _migrate(database_url)
    asyncio.run(seed_demo(database_url))
    return database_url


def test_seed_creates_expected_entity_counts(seeded_database_url: str) -> None:
    with _session(seeded_database_url) as session:
        assert _count(session, Region) == 227
        assert _count(session, Indicator) == 15
        assert _count(session, DataValue) == 1608
        assert _count(session, RegionAlias) == 1
        assert _count(session, DataSource) == 1
        assert _count(session, ImportJob) == 1

        job = session.execute(select(ImportJob)).scalar_one()
        assert job.filename == "seed_demo.py"
        assert job.job_type == "manual"
        assert job.status == "success"
        assert job.mode == "atomic"
        assert job.total_rows == 1608
        assert job.success_rows == 1608
        assert job.error_rows == 0

        source = session.execute(select(DataSource)).scalar_one()
        assert source.name == "演示数据（合成）"
        assert source.source_type == "demo"
        assert source.owner == "seed_demo"


def test_applicability_row_counts(seeded_database_url: str) -> None:
    with _session(seeded_database_url) as session:
        assert _data_value_count(session, level="district") == 15
        assert (
            _data_value_count(
                session, level="town", category="administrative"
            )
            == 104
        )
        assert (
            _data_value_count(session, level="town", category="development_zone")
            == 12
        )
        assert _data_value_count(session, level="village") == 1477

        assert _data_value_count(session, indicator_code="gdp") == 3
        assert _data_value_count(session, indicator_code="admin_village_count") == 14
        assert _data_value_count(session, indicator_code="farmland_area") == 225
        assert _data_value_count(session, indicator_code="forest_area") == 225

        assert _count(session, Region) == 227
        district_count = session.execute(
            select(func.count()).select_from(Region).where(Region.level == "district")
        ).scalar_one()
        town_count = session.execute(
            select(func.count()).select_from(Region).where(Region.level == "town")
        ).scalar_one()
        village_count = session.execute(
            select(func.count()).select_from(Region).where(Region.level == "village")
        ).scalar_one()
        assert (district_count, town_count, village_count) == (1, 15, 211)


def test_text_values_are_synthetic_and_within_limits(
    seeded_database_url: str,
) -> None:
    with _session(seeded_database_url) as session:
        intro_values = session.execute(
            select(DataValue.value_text)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(Indicator.code == "region_intro")
        ).scalars().all()
        feature_values = session.execute(
            select(DataValue.value_text)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(Indicator.code == "region_feature")
        ).scalars().all()

        intro_texts = [value for value in intro_values if value is not None]
        feature_texts = [value for value in feature_values if value is not None]

        assert len(intro_texts) == len(intro_values) == 227
        assert len(feature_texts) == len(feature_values) == 227
        assert max(len(value) for value in intro_texts) <= 150
        assert max(len(value) for value in feature_texts) <= 300
        assert all("演示" in value for value in intro_texts)
        assert all("演示" in value for value in feature_texts)


def test_missing_values_are_null_and_bounded(seeded_database_url: str) -> None:
    with _session(seeded_database_url) as session:
        missing_count = session.execute(
            select(func.count())
            .select_from(DataValue)
            .where(DataValue.quality_status == "missing")
        ).scalar_one()
        assert missing_count > 0

        invalid_missing = session.execute(
            select(func.count())
            .select_from(DataValue)
            .where(
                DataValue.quality_status == "missing",
                or_(
                    DataValue.value_number.is_not(None),
                    DataValue.value_text.is_not(None),
                ),
            )
        ).scalar_one()
        assert invalid_missing == 0

        non_district_numeric = session.execute(
            select(func.count())
            .select_from(DataValue)
            .join(Region, DataValue.region_id == Region.id)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                Region.level != "district",
                Indicator.value_type != "long_text",
            )
        ).scalar_one()
        ratio = missing_count / non_district_numeric
        assert 0.02 <= ratio <= 0.04


def test_no_gdp_rows_for_administrative_towns_or_villages(
    seeded_database_url: str,
) -> None:
    with _session(seeded_database_url) as session:
        forbidden = session.execute(
            select(func.count())
            .select_from(DataValue)
            .join(Region, DataValue.region_id == Region.id)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                Indicator.code == "gdp",
                or_(
                    Region.level == "village",
                    and_(
                        Region.level == "town",
                        Region.category == "administrative",
                    ),
                ),
            )
        ).scalar_one()
        assert forbidden == 0


def test_alias_and_development_zone_regions(seeded_database_url: str) -> None:
    with _session(seeded_database_url) as session:
        alias_target = session.execute(
            select(Region.name)
            .join(RegionAlias, RegionAlias.region_id == Region.id)
            .where(RegionAlias.alias == "玉窖镇")
        ).scalar_one()
        assert alias_target == "玉滘镇"

        zones = session.execute(
            select(Region).where(Region.category == "development_zone")
        ).scalars().all()
        assert {zone.name for zone in zones} == {
            "揭东经济开发区",
            "揭东中德金属生态城",
        }
        assert all(zone.level == "town" for zone in zones)

        zone_ids = [zone.id for zone in zones]
        zone_villages = session.execute(
            select(func.count())
            .select_from(Region)
            .where(
                Region.level == "village",
                Region.parent_id.in_(zone_ids),
            )
        ).scalar_one()
        assert zone_villages == 0


def test_check_mode_reports_counts_without_writing(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'check.db').as_posix()}"
    _migrate(database_url)

    summary = asyncio.run(seed_demo(database_url, check=True))

    assert summary["mode"] == "check"
    assert summary["fixture_regions"] == 227
    assert summary["indicators"] == 15
    assert summary["expected_data_values"] == 1608
    assert summary["applicability"] == EXPECTED_APPLICABILITY
    assert summary["existing"] == {
        "regions": 0,
        "indicators": 0,
        "data_values": 0,
        "region_aliases": 0,
        "data_sources": 0,
        "import_jobs": 0,
    }

    with _session(database_url) as session:
        assert _count(session, Region) == 0
        assert _count(session, DataValue) == 0


def test_second_seed_run_is_idempotent(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'idempotent.db').as_posix()}"
    _migrate(database_url)
    asyncio.run(seed_demo(database_url))

    with _session(database_url) as session:
        first_counts = (
            _count(session, Region),
            _count(session, Indicator),
            _count(session, DataValue),
            _count(session, RegionAlias),
            _count(session, DataSource),
            _count(session, ImportJob),
        )
        sample = session.execute(
            select(Region.code, Indicator.code, DataValue.value_number)
            .join(Region, DataValue.region_id == Region.id)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                DataValue.quality_status == "verified",
                DataValue.value_number.is_not(None),
            )
            .order_by(DataValue.id)
        ).first()
        assert sample is not None
        sample_region_code, sample_indicator_code, sample_value = sample

    asyncio.run(seed_demo(database_url))

    with _session(database_url) as session:
        second_counts = (
            _count(session, Region),
            _count(session, Indicator),
            _count(session, DataValue),
            _count(session, RegionAlias),
            _count(session, DataSource),
            _count(session, ImportJob),
        )
        second_value = session.execute(
            select(DataValue.value_number)
            .join(Region, DataValue.region_id == Region.id)
            .join(Indicator, DataValue.indicator_id == Indicator.id)
            .where(
                Region.code == sample_region_code,
                Indicator.code == sample_indicator_code,
            )
        ).scalar_one()

    assert first_counts == second_counts == (227, 15, 1608, 1, 1, 1)
    assert second_value == sample_value
