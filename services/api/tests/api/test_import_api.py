"""API tests for the minimal Excel import pipeline."""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import DataValue, Indicator, Region
from tests.api.helpers import auth_client, bearer, create_user, login_token

PASSWORD = "Passw0rd123"
HEADERS = ["区域类型", "区域名称", "数据名称", "数据期", "单位", "数据值"]


@pytest.fixture()
def api(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    with auth_client(tmp_path, seeded=True, filename="import_api.db") as (client, database_path):
        create_user(
            database_path,
            username="editor01",
            password=PASSWORD,
            role="editor",
            phone="13600000001",
        )
        create_user(
            database_path,
            username="viewer01",
            password=PASSWORD,
            role="viewer",
            phone="13600000002",
        )
        yield client, database_path


def _workbook(rows: Sequence[Sequence[object]], headers: list[str] | None = None) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(headers or HEADERS)
    for row in rows:
        worksheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _upload(
    client: TestClient,
    token: str,
    rows: Sequence[Sequence[object]],
    *,
    mode: str = "atomic",
    headers: list[str] | None = None,
) -> dict:
    response = client.post(
        "/api/v1/admin/imports",
        headers=bearer(token),
        files={
            "file": (
                "demo.xlsx",
                _workbook(rows, headers),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"mode": mode},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _region_id(client: TestClient, name: str) -> int:
    response = client.get("/api/v1/regions", params={"q": name, "level": "town"})
    assert response.status_code == 200
    matches = [item for item in response.json()["data"] if item["name"] == name]
    assert matches
    return matches[0]["id"]


def _data_values(
    client: TestClient,
    *,
    region_id: int,
    indicator_code: str,
) -> list[dict]:
    response = client.get(
        "/api/v1/data-values",
        params={
            "region_id": region_id,
            "indicator_code": indicator_code,
            "period_year": 2025,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _stored_value(database_path: Path, region_name: str, indicator_code: str) -> DataValue:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            row = session.execute(
                select(DataValue)
                .join(Region, DataValue.region_id == Region.id)
                .join(Indicator, DataValue.indicator_id == Indicator.id)
                .where(Region.name == region_name, Indicator.code == indicator_code)
            ).scalars().one()
            return row
    finally:
        engine.dispose()


def test_valid_atomic_import_writes_values(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [
        ("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", 123.45),
        ("镇街", "云路镇", "地区生产总值", "2025", "亿元", 98.7),
    ]

    job = _upload(client, token, rows)

    assert job["status"] == "success"
    assert job["total_rows"] == 2
    assert job["success_rows"] == 2
    assert job["error_rows"] == 0
    assert job["errors"] == []

    detail = client.get(f"/api/v1/admin/imports/{job['id']}", headers=bearer(token))
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "success"

    errors = client.get(f"/api/v1/admin/imports/{job['id']}/errors", headers=bearer(token))
    assert errors.status_code == 200
    assert errors.json()["data"]["errors"] == []

    region_id = _region_id(client, "曲溪街道")
    values = _data_values(client, region_id=region_id, indicator_code="gdp")
    assert len(values) == 1
    assert values[0]["value_number"] == 123.45
    assert values[0]["quality_status"] == "verified"


def test_invalid_atomic_import_writes_nothing(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [
        ("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", 123.45),
        ("镇街", "云路镇", "地区生产总值", "2025", "亩", 98.7),
    ]

    job = _upload(client, token, rows)

    assert job["status"] == "failed"
    assert job["success_rows"] == 0
    assert job["error_rows"] == 1
    codes = {issue["code"] for issue in job["errors"]}
    assert "UNIT_MISMATCH" in codes
    unit_error = next(issue for issue in job["errors"] if issue["code"] == "UNIT_MISMATCH")
    assert unit_error["row_number"] == 3

    region_id = _region_id(client, "曲溪街道")
    assert _data_values(client, region_id=region_id, indicator_code="gdp") == []


def test_partial_import_writes_valid_rows(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [
        ("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", 123.45),
        ("镇街", "云路镇", "地区生产总值", "2025", "亩", 98.7),
    ]

    job = _upload(client, token, rows, mode="partial")

    assert job["status"] == "partial"
    assert job["success_rows"] == 1
    assert job["error_rows"] == 1

    valid_region = _region_id(client, "曲溪街道")
    invalid_region = _region_id(client, "云路镇")
    assert len(_data_values(client, region_id=valid_region, indicator_code="gdp")) == 1
    assert _data_values(client, region_id=invalid_region, indicator_code="gdp") == []


def test_empty_value_writes_missing_not_zero(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", "")]

    job = _upload(client, token, rows)

    assert job["status"] == "success"
    assert any(issue["code"] == "EMPTY_VALUE" for issue in job["errors"])

    region_id = _region_id(client, "曲溪街道")
    values = _data_values(client, region_id=region_id, indicator_code="gdp")
    assert len(values) == 1
    assert values[0]["value_number"] is None
    assert values[0]["value_text"] is None
    assert values[0]["quality_status"] == "missing"


def test_reimport_increments_version(api: tuple[TestClient, Path]) -> None:
    client, database_path = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", 123.45)]

    first = _upload(client, token, rows)
    second = _upload(client, token, rows)

    assert first["status"] == "success"
    assert second["status"] == "success"
    stored = _stored_value(database_path, "曲溪街道", "gdp")
    assert stored.version == 2
    assert stored.import_job_id == second["id"]


def test_missing_header_fails_the_job(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    rows = [("镇街", "曲溪街道", "地区生产总值", "2025", 123.45)]
    headers = ["区域类型", "区域名称", "数据名称", "数据期", "数据值"]

    job = _upload(client, token, rows, headers=headers)

    assert job["status"] == "failed"
    assert any(issue["code"] == "HEADER_MISSING" for issue in job["errors"])
    assert job["success_rows"] == 0


def test_import_list_contains_created_jobs(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "editor01", PASSWORD)
    job = _upload(client, token, [("镇街", "曲溪街道", "地区生产总值", "2025", "亿元", 1)])

    response = client.get("/api/v1/admin/imports", headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total"] >= 1
    assert body["data"][0]["id"] == job["id"]


def test_viewer_cannot_import(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "viewer01", PASSWORD)

    response = client.post(
        "/api/v1/admin/imports",
        headers=bearer(token),
        files={"file": ("demo.xlsx", _workbook([]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"mode": "atomic"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
