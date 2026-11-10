"""End-to-end tests for the B04 read-only query APIs."""
from __future__ import annotations

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import DataValue, Indicator, Region


def _sync_database_url(client: TestClient) -> str:
    app = cast(FastAPI, client.app)
    async_url = app.state.settings.database_url
    return async_url.replace("sqlite+aiosqlite:///", "sqlite:///")


def test_envelope_carries_request_id(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/regions", params={"level": "town"})

    assert response.status_code == 200
    body = response.json()
    request_id = response.headers["X-Request-ID"]
    assert request_id
    assert body["meta"]["request_id"] == request_id


def test_region_list_town_level_and_pagination(seeded_client: TestClient) -> None:
    first_page = seeded_client.get(
        "/api/v1/regions",
        params={"level": "town", "page": 1, "page_size": 10},
    )

    assert first_page.status_code == 200
    body = first_page.json()
    assert body["meta"]["total"] == 15
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 10
    assert body["meta"]["has_next"] is True
    assert len(body["data"]) == 10

    second_page = seeded_client.get(
        "/api/v1/regions",
        params={"level": "town", "page": 2, "page_size": 10},
    )

    assert second_page.status_code == 200
    second_body = second_page.json()
    assert second_body["meta"]["total"] == 15
    assert second_body["meta"]["has_next"] is False
    assert len(second_body["data"]) == 5


def test_region_tree_depth_one_has_root_and_town_children(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/regions/tree", params={"depth": 1})

    assert response.status_code == 200
    root = response.json()["data"]
    assert root["code"] == "JD"
    assert root["level"] == "district"
    assert len(root["children"]) == 15
    assert all(child["children"] == [] for child in root["children"])
    assert root["children"][0]["code"] == "JD-T-01"


def test_region_detail_missing_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/regions/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_quxi_profile_has_text_and_metrics(seeded_client: TestClient) -> None:
    search = seeded_client.get("/api/v1/regions", params={"q": "曲溪"})

    assert search.status_code == 200
    matches = search.json()["data"]
    assert matches
    region = matches[0]
    assert region["level"] == "town"

    response = seeded_client.get(f"/api/v1/regions/{region['id']}/profile")

    assert response.status_code == 200
    profile = response.json()["data"]
    assert profile["intro"]
    assert profile["feature"]
    assert profile["metrics"]
    assert "region_intro" in profile["applicable_indicator_codes"]
    assert "population_resident" in profile["applicable_indicator_codes"]
    assert profile["data_as_of"]


def test_development_zone_profile_omits_non_applicable_indicators(
    seeded_client: TestClient,
) -> None:
    towns = seeded_client.get(
        "/api/v1/regions",
        params={"level": "town", "page_size": 100},
    )
    assert towns.status_code == 200
    zones = [item for item in towns.json()["data"] if item["category"] == "development_zone"]
    assert len(zones) == 2

    response = seeded_client.get(f"/api/v1/regions/{zones[0]['id']}/profile")

    assert response.status_code == 200
    profile = response.json()["data"]
    metric_codes = {metric["code"] for metric in profile["metrics"]}
    applicable_codes = set(profile["applicable_indicator_codes"])
    for forbidden in ("farmland_area", "forest_area", "admin_village_count"):
        assert forbidden not in metric_codes
        assert forbidden not in applicable_codes


def test_indicator_list_returns_fifteen(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/indicators")

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 15
    codes = {item["code"] for item in body["data"]}
    assert "population_resident" in codes
    assert "region_intro" in codes
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_indicator_detail_and_missing(seeded_client: TestClient) -> None:
    listing = seeded_client.get("/api/v1/indicators").json()["data"]
    indicator = listing[0]

    found = seeded_client.get(f"/api/v1/indicators/{indicator['id']}")
    assert found.status_code == 200
    assert found.json()["data"]["code"] == indicator["code"]

    missing = seeded_client.get("/api/v1/indicators/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


def test_data_values_by_region_and_indicator(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/api/v1/data-values",
        params={
            "region_code": "JD",
            "indicator_code": "population_resident",
            "period_year": 2025,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert len(body["data"]) == 1
    row = body["data"][0]
    assert row["region_code"] == "JD"
    assert row["indicator_code"] == "population_resident"
    assert row["value_number"] is not None
    assert isinstance(row["value_number"], (int, float))
    assert row["quality_status"] == "verified"


def test_data_values_empty_for_development_zone_village_count(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get(
        "/api/v1/data-values",
        params={
            "region_code": "JD-Z-01",
            "indicator_code": "admin_village_count",
            "period_year": 2025,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


def test_rank_population_town_limit_without_development_zones(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get(
        "/api/v1/data-values/rank",
        params={
            "indicator_code": "population_resident",
            "level": "town",
            "limit": 5,
            "include_development_zones": "false",
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = body["data"]
    assert len(items) == 5
    values = [item["value_number"] for item in items]
    assert all(value is not None for value in values)
    assert values == sorted(values, reverse=True)
    assert [item["rank"] for item in items] == [1, 2, 3, 4, 5]
    assert body["meta"]["level"] == "town"
    assert body["meta"]["order"] == "desc"
    assert body["meta"]["limit"] == 5
    assert body["meta"]["include_development_zones"] is False


def test_rank_text_indicator_returns_422(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/api/v1/data-values/rank",
        params={"indicator_code": "region_intro", "level": "town"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INDICATOR_NOT_NUMERIC"


def test_compare_two_regions_preserves_order(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/api/v1/data-values/compare",
        params={
            "indicator_code": "population_resident",
            "region_codes": "JD-T-01,JD-T-02",
            "period_year": 2025,
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = body["data"]
    assert [item["region_code"] for item in items] == ["JD-T-01", "JD-T-02"]
    assert all(item["unit"] == "人" for item in items)
    assert body["meta"]["requested_count"] == 2

    first, second = items
    if first["value_number"] is not None and second["value_number"] is not None:
        assert second["diff_from_first"] == pytest.approx(
            second["value_number"] - first["value_number"], abs=1e-4
        )
        assert second["diff_pct_from_first"] is not None


def test_compare_validation_errors(seeded_client: TestClient) -> None:
    text = seeded_client.get(
        "/api/v1/data-values/compare",
        params={
            "indicator_code": "region_feature",
            "region_codes": "JD-T-01,JD-T-02",
        },
    )
    assert text.status_code == 422
    assert text.json()["error"]["code"] == "INDICATOR_NOT_NUMERIC"

    too_few = seeded_client.get(
        "/api/v1/data-values/compare",
        params={"indicator_code": "population_resident", "region_codes": "JD-T-01"},
    )
    assert too_few.status_code == 422
    assert too_few.json()["error"]["code"] == "COMPARE_REGION_COUNT_INVALID"


def test_dashboard_overview_core_metrics(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["period_year"] == 2025
    assert data["town_count"] == 15
    assert data["data_as_of"]
    assert len(data["metrics"]) == 6

    metrics = {metric["code"]: metric for metric in data["metrics"]}
    assert set(metrics) == {
        "area",
        "population_resident",
        "population_household",
        "gdp",
        "budget_revenue",
        "admin_village_count",
    }
    for metric in metrics.values():
        assert metric["label"]
        assert metric["unit"]
        assert metric["quality_status"] in {
            "missing",
            "not_applicable",
            "suppressed",
            "estimated",
            "provisional",
            "verified",
        }
        assert metric["value_number"] is None or isinstance(
            metric["value_number"], (int, float)
        )


def test_missing_value_is_null_not_zero(seeded_client: TestClient) -> None:
    engine = create_engine(_sync_database_url(seeded_client))
    try:
        with Session(engine) as session:
            missing = session.execute(
                select(Region.code, Indicator.code, DataValue.period_year)
                .select_from(DataValue)
                .join(Region, DataValue.region_id == Region.id)
                .join(Indicator, DataValue.indicator_id == Indicator.id)
                .where(
                    DataValue.quality_status == "missing",
                    DataValue.value_number.is_(None),
                )
                .order_by(DataValue.id)
            ).first()
    finally:
        engine.dispose()

    assert missing is not None
    region_code, indicator_code, period_year = missing

    response = seeded_client.get(
        "/api/v1/data-values",
        params={
            "region_code": region_code,
            "indicator_code": indicator_code,
            "period_year": period_year,
        },
    )

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["value_number"] is None
    assert rows[0]["quality_status"] == "missing"


def test_public_list_defaults_and_quality_filter(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/data-values")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["page_size"] == 20
    assert len(body["data"]) == 20

    filtered = seeded_client.get(
        "/api/v1/data-values",
        params={"quality_status": "missing", "page_size": 100},
    )

    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["meta"]["total"] == 42
    assert all(row["quality_status"] == "missing" for row in filtered_body["data"])


def test_region_category_filter_returns_development_zones(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/api/v1/regions",
        params={"level": "town", "category": "development_zone", "page_size": 100},
    )

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 2
    assert all(row["category"] == "development_zone" for row in rows)
    assert {row["code"] for row in rows} >= {"JD-Z-01", "JD-Z-02"}


def test_indicator_value_type_filter_returns_text_indicators(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/indicators", params={"value_type": "long_text"})

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 2
    assert {row["code"] for row in rows} == {"region_intro", "region_feature"}


def test_dashboard_overview_reports_full_numeric_coverage(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/dashboard/overview", params={"period_year": 2025})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["town_count"] == 15
    assert body["coverage"] == 100.0
    assert len(body["metrics"]) == 6
