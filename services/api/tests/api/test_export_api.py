"""API tests for export snapshots, formats, permissions, expiry, and audit."""
from __future__ import annotations

import asyncio
import csv
import io
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from openpyxl import load_workbook
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.models import AuditLog, ChatMessage, ChatSession, ExportJob
from scripts.seed_demo import seed_demo
from tests.api.helpers import (
    TEST_JWT_SECRET,
    alembic_config,
    bearer,
    create_user,
    login_token,
)

API = "/api/v1"


@pytest.fixture()
def env(tmp_path: Path) -> Iterator[tuple[TestClient, Path, Path]]:
    database_path = tmp_path / "export.db"
    export_dir = tmp_path / "exports"
    sync_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(alembic_config(sync_url), "head")
    asyncio.run(seed_demo(sync_url))
    app = create_app(
        settings=Settings(
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            jwt_secret=SecretStr(TEST_JWT_SECRET),
            export_dir=str(export_dir),
        )
    )
    with TestClient(app) as client:
        yield client, database_path, export_dir


def _token(client: TestClient, database_path: Path, username: str, role: str = "viewer") -> str:
    create_user(
        database_path,
        username=username,
        password="Password1234",
        role=role,
        display_name=f"{username}-显示名",
    )
    return login_token(client, username, "Password1234")


def _citation() -> dict[str, Any]:
    return {
        "id": "c1",
        "citation_id": "c1",
        "indicator": "常住人口",
        "indicator_name": "常住人口",
        "indicator_code": "population_resident",
        "region": "云路镇",
        "region_code": "JD-T-02",
        "region_name": "云路镇",
        "region_level": "town",
        "period": "2025",
        "source": "data_values",
        "data_as_of": "2026-11-10",
    }


def _insert_answer(
    database_path: Path,
    *,
    user_id: int,
    answer_id: str,
    blocks: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    markdown: str = "测试答案。",
) -> None:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            chat_session = ChatSession(user_id=user_id, title="导出测试")
            session.add(chat_session)
            session.flush()
            session.add(
                ChatMessage(
                    session_id=chat_session.id,
                    role="assistant",
                    content=markdown,
                    answer_id=answer_id,
                    blocks=blocks,
                    citations=citations,
                    data_snapshot={
                        "answer_id": answer_id,
                        "demo": True,
                        "data_version": "dv_test",
                        "data_hash": "sha256:" + "0" * 64,
                        "registry_version": "1.0.0",
                        "generated_at": "2026-11-10T10:00:00+08:00",
                        "period": "2025",
                    },
                )
            )
            session.commit()
    finally:
        engine.dispose()


def _null_zero_snapshot(database_path: Path, user_id: int) -> str:
    answer_id = "ans_test_nullzero"
    citation = _citation()
    blocks = [
        {
            "id": "b1",
            "type": "table",
            "component": "data_table",
            "props": {"title": "空值与零值"},
            "title": "空值与零值",
            "columns": ["区域", "值"],
            "rows": [["空值", None], ["零值", 0]],
            "citations": [citation],
        },
        {
            "id": "b2",
            "type": "source",
            "component": "source_card",
            "props": {},
            "title": "引用与来源",
            "citations": [citation],
        },
    ]
    _insert_answer(
        database_path,
        user_id=user_id,
        answer_id=answer_id,
        blocks=blocks,
        citations=[citation],
    )
    return answer_id


def _report_payload(client: TestClient, fmt: str | None, **source: Any) -> dict[str, Any]:
    region = next(
        item
        for item in client.get(f"{API}/regions", params={"q": "云路镇"}).json()["data"]
        if item["name"] == "云路镇"
    )
    payload: dict[str, Any] = {
        "source_type": "report",
        "title": "2025 年云路镇常住人口",
        "source": {
            "region_id": region["id"],
            "indicator_code": "population_resident",
            "period_year": 2025,
            **source,
        },
    }
    if fmt is not None:
        payload["format"] = fmt
    return payload


def _expected_value(client: TestClient) -> float:
    response = client.get(
        f"{API}/data-values",
        params={
            "region_code": "JD-T-02",
            "indicator_code": "population_resident",
            "period_year": 2025,
        },
    )
    return float(response.json()["data"][0]["value_number"])


def test_report_csv_uses_database_values(env: tuple[TestClient, Path, Path]) -> None:
    client, _, _ = env
    token = _token(client, env[1], "csvviewer")
    headers = bearer(token)
    response = client.post(
        f"{API}/exports",
        headers=headers,
        json=_report_payload(client, "csv", unit="错误单位"),
    )
    assert response.status_code == 201, response.text
    job = response.json()["data"]
    assert job["status"] == "ready"
    assert job["progress"] == 100
    assert job["file_size"] > 0
    assert job["download_url"] == f"{API}/exports/{job['export_id']}/download"
    assert job["created_at"].endswith("+08:00")

    download = client.get(job["download_url"], headers=headers)
    assert download.status_code == 200
    body = download.content.decode("utf-8-sig")
    assert "错误单位" not in body
    assert str(int(_expected_value(client))) in body


def test_csv_preserves_null_and_zero(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    user_id = create_user(
        database_path,
        username="csvnull",
        password="Password1234",
        role="viewer",
    )
    token = login_token(client, "csvnull", "Password1234")
    headers = bearer(token)
    answer_id = _null_zero_snapshot(database_path, user_id)
    response = client.post(
        f"{API}/exports",
        headers=headers,
        json={"source_type": "answer", "source_id": answer_id, "format": "csv", "title": "空值测试"},
    )
    assert response.status_code == 201, response.text
    job = response.json()["data"]
    assert job["status"] == "ready", job
    body = client.get(job["download_url"], headers=headers).content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(body)))
    null_row = next(row for row in rows if row and row[0] == "空值")
    zero_row = next(row for row in rows if row and row[0] == "零值")
    assert null_row[1] == ""
    assert zero_row[1] == "0"


def test_xlsx_has_three_sheets_and_no_zero_fill(
    env: tuple[TestClient, Path, Path],
) -> None:
    client, database_path, _ = env
    user_id = create_user(
        database_path,
        username="xlsxuser",
        password="Password1234",
        role="viewer",
    )
    token = login_token(client, "xlsxuser", "Password1234")
    headers = bearer(token)
    answer_id = _null_zero_snapshot(database_path, user_id)
    response = client.post(
        f"{API}/exports",
        headers=headers,
        json={"source_type": "answer", "source_id": answer_id, "format": "xlsx"},
    )
    job = response.json()["data"]
    assert job["status"] == "ready", job
    content = client.get(job["download_url"], headers=headers).content
    workbook = load_workbook(io.BytesIO(content))
    assert workbook.sheetnames == ["答案摘要", "数据", "引用"]

    data_sheet = workbook["数据"]
    rows = list(data_sheet.iter_rows(values_only=True))
    null_row = next(row for row in rows if row and row[0] == "空值")
    zero_row = next(row for row in rows if row and row[0] == "零值")
    assert null_row[1] is None
    assert zero_row[1] == 0
    formulas = [
        cell
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
        if cell.data_type == "f"
    ]
    assert formulas == []


def test_png_and_pdf_are_rendered(env: tuple[TestClient, Path, Path]) -> None:
    pytest.importorskip("playwright")
    client, database_path, _ = env
    user_id = create_user(
        database_path,
        username="imageuser",
        password="Password1234",
        role="viewer",
    )
    token = login_token(client, "imageuser", "Password1234")
    headers = bearer(token)
    answer_id = _null_zero_snapshot(database_path, user_id)

    for fmt, signature, limit in (
        ("png", b"\x89PNG", 3 * 1024 * 1024),
        ("pdf", b"%PDF", 10 * 1024 * 1024),
    ):
        response = client.post(
            f"{API}/exports",
            headers=headers,
            json={"source_type": "answer", "source_id": answer_id, "format": fmt},
        )
        job = response.json()["data"]
        if job["status"] != "ready":
            pytest.skip(f"browser renderer unavailable: {job['error']}")
        download = client.get(job["download_url"], headers=headers)
        assert download.status_code == 200
        assert download.content.startswith(signature)
        assert 0 < len(download.content) <= limit
        assert len(download.content) == job["file_size"]


def test_format_is_required(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    token = _token(client, database_path, "fmtuser")
    response = client.post(
        f"{API}/exports",
        headers=bearer(token),
        json=_report_payload(client, None),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXPORT_FORMAT_REQUIRED"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            assert session.execute(select(func.count()).select_from(ExportJob)).scalar_one() == 0
    finally:
        engine.dispose()


def test_invalid_format_is_rejected(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    token = _token(client, database_path, "badfmt")
    response = client.post(
        f"{API}/exports",
        headers=bearer(token),
        json=_report_payload(client, "docx"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXPORT_FORMAT_UNSUPPORTED"


def test_guest_cannot_export(env: tuple[TestClient, Path, Path]) -> None:
    client, _, _ = env
    response = client.post(f"{API}/exports", json=_report_payload(client, "csv"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EXPORT_FORBIDDEN"


def test_answer_source_must_exist(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    token = _token(client, database_path, "nosource")
    response = client.post(
        f"{API}/exports",
        headers=bearer(token),
        json={"source_type": "answer", "source_id": "ans_missing", "format": "csv"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXPORT_SOURCE_NOT_FOUND"


def test_other_users_answer_is_not_visible(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    owner_id = create_user(
        database_path,
        username="answerowner",
        password="Password1234",
        role="viewer",
    )
    _token(client, database_path, "answerother")
    other_token = login_token(client, "answerother", "Password1234")
    answer_id = _null_zero_snapshot(database_path, owner_id)
    response = client.post(
        f"{API}/exports",
        headers=bearer(other_token),
        json={"source_type": "answer", "source_id": answer_id, "format": "csv"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXPORT_SOURCE_NOT_FOUND"


def test_download_ownership_and_admin_override(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    owner_token = _token(client, database_path, "jobowner")
    other_token = _token(client, database_path, "jobother")
    admin_token = _token(client, database_path, "jobadmin", role="admin")
    created = client.post(
        f"{API}/exports",
        headers=bearer(owner_token),
        json=_report_payload(client, "csv"),
    ).json()["data"]
    url = created["download_url"]

    denied = client.get(url, headers=bearer(other_token))
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "EXPORT_FORBIDDEN"
    assert client.get(url, headers=bearer(owner_token)).status_code == 200
    assert client.get(url, headers=bearer(admin_token)).status_code == 200


def test_expired_export_returns_410(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    token = _token(client, database_path, "expireduser")
    headers = bearer(token)
    created = client.post(
        f"{API}/exports",
        headers=headers,
        json=_report_payload(client, "csv"),
    ).json()["data"]
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE export_jobs SET expires_at = :value WHERE export_id = :id"),
                {
                    "value": datetime.now(timezone.utc) - timedelta(days=1),
                    "id": created["export_id"],
                },
            )
    finally:
        engine.dispose()
    response = client.get(created["download_url"], headers=headers)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "EXPORT_EXPIRED"


def test_export_writes_audit_and_counts_downloads(env: tuple[TestClient, Path, Path]) -> None:
    client, database_path, _ = env
    user_id = create_user(
        database_path,
        username="audituser",
        password="Password1234",
        role="viewer",
    )
    token = login_token(client, "audituser", "Password1234")
    headers = bearer(token)
    created = client.post(
        f"{API}/exports",
        headers=headers,
        json=_report_payload(client, "csv"),
    ).json()["data"]
    client.get(created["download_url"], headers=headers)
    client.get(created["download_url"], headers=headers)

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            actions = [
                item.action
                for item in session.execute(
                    select(AuditLog).where(AuditLog.resource_id == created["export_id"])
                ).scalars()
            ]
            job = session.execute(
                select(ExportJob).where(ExportJob.export_id == created["export_id"])
            ).scalars().one()
    finally:
        engine.dispose()
    assert "export.requested" in actions
    assert "export.ready" in actions
    assert "export.downloaded" in actions
    assert job.download_count == 2
    assert job.user_id == user_id
