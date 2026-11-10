"""API tests for the deterministic AI agent, persistence, and the mocked LLM path."""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.ai.rate_limit import reset_rate_limits
from app.core.config import Settings
from app.main import create_app
from app.models import AuditLog, ChatMessage, ChatSession
from scripts.seed_demo import seed_demo
from tests.api.helpers import (
    TEST_JWT_SECRET,
    alembic_config,
    auth_client,
    bearer,
    create_user,
    login_token,
)

API = "/api/v1"


@pytest.fixture(autouse=True)
def _reset_limits() -> None:
    reset_rate_limits()


@pytest.fixture()
def seeded(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    with auth_client(tmp_path, seeded=True, filename="ai.db") as pair:
        yield pair


def _count(database_path: Path, model: Any) -> int:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            return int(session.execute(select(func.count()).select_from(model)).scalar_one())
    finally:
        engine.dispose()


def _audits(database_path: Path, action: str) -> list[AuditLog]:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            return list(
                session.execute(select(AuditLog).where(AuditLog.action == action)).scalars()
            )
    finally:
        engine.dispose()


def test_lookup_returns_real_value_and_citation(seeded: tuple[TestClient, Path]) -> None:
    client, _ = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "2025 年云路镇常住人口"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "done"
    assert data["intent"] == "lookup"
    assert data["demo"] is True
    assert data["meta"]["tool_calls"] >= 1
    types = [block["type"] for block in data["blocks"]]
    assert "metric_grid" in types
    assert "source" in types
    assert data["citations"]

    expected = client.get(
        f"{API}/data-values",
        params={
            "region_code": "JD-T-02",
            "indicator_code": "population_resident",
            "period_year": 2025,
        },
    ).json()["data"][0]["value_number"]
    grid = next(block for block in data["blocks"] if block["type"] == "metric_grid")
    assert grid["metrics"][0]["value"] == expected


def test_seeded_missing_value_is_reported_not_fabricated(
    seeded: tuple[TestClient, Path],
) -> None:
    client, _ = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "2025 年曲溪街道常住人口"})
    data = response.json()["data"]
    assert data["status"] == "no_data"
    assert [block["type"] for block in data["blocks"]] == ["notice"]
    assert data["citations"] == []


def test_rank_returns_top_five_with_real_values(seeded: tuple[TestClient, Path]) -> None:
    client, _ = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "2025 年各镇街常住人口排名前 5"})
    data = response.json()["data"]
    assert data["intent"] == "rank"
    types = [block["type"] for block in data["blocks"]]
    for expected in ("ranking", "table", "chart", "source"):
        assert expected in types
    ranking = next(block for block in data["blocks"] if block["type"] == "ranking")["ranking"]
    assert len(ranking) == 5
    api_rows = client.get(
        f"{API}/data-values/rank",
        params={"indicator_code": "population_resident", "period_year": 2025, "limit": 5},
    ).json()["data"]
    assert [item["value"] for item in ranking] == [row["value_number"] for row in api_rows]
    assert data["chart_spec"]["type"] == "hbar"


def test_compare_returns_table_and_chart(seeded: tuple[TestClient, Path]) -> None:
    client, _ = seeded
    response = client.post(
        f"{API}/ai/chat",
        json={"question": "比较曲溪街道和云路镇常住人口"},
    )
    data = response.json()["data"]
    assert data["intent"] == "compare"
    types = [block["type"] for block in data["blocks"]]
    assert "table" in types and "chart" in types
    table = next(block for block in data["blocks"] if block["type"] == "table")
    api_rows = client.get(
        f"{API}/data-values/compare",
        params={
            "indicator_code": "population_resident",
            "region_codes": "JD-T-01,JD-T-02",
            "period_year": 2025,
        },
    ).json()["data"]
    assert [row[0] for row in table["rows"]] == [row["region_name"] for row in api_rows]
    assert [row[1] for row in table["rows"]] == [row["value_number"] for row in api_rows]


def test_profile_returns_summary_and_metric_grid(seeded: tuple[TestClient, Path]) -> None:
    client, _ = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "介绍玉湖镇"})
    data = response.json()["data"]
    assert data["intent"] == "profile"
    types = [block["type"] for block in data["blocks"]]
    assert "summary" in types and "metric_grid" in types
    grid = next(block for block in data["blocks"] if block["type"] == "metric_grid")
    assert grid["metrics"]
    assert all(item["citation_id"] for item in grid["metrics"] if item["value"] is not None)

    region = next(
        item
        for item in client.get(f"{API}/regions", params={"q": "玉湖镇"}).json()["data"]
        if item["name"] == "玉湖镇"
    )
    profile = client.get(f"{API}/regions/{region['id']}/profile").json()["data"]
    profile_values = {
        metric["name"]: metric["value_number"] for metric in profile["metrics"]
    }
    for item in grid["metrics"]:
        if item["value"] is not None:
            assert item["value"] == profile_values[item["label"]]


def test_unknown_entity_returns_notice_without_numbers(
    seeded: tuple[TestClient, Path],
) -> None:
    client, _ = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "火星基地常住人口"})
    data = response.json()["data"]
    assert data["status"] == "no_data"
    assert [block["type"] for block in data["blocks"]] == ["notice"]
    assert not any(
        block["type"] in {"metric_grid", "chart", "table", "ranking"}
        for block in data["blocks"]
    )


def test_guest_does_not_persist_history(seeded: tuple[TestClient, Path]) -> None:
    client, database_path = seeded
    response = client.post(f"{API}/ai/chat", json={"question": "2025 年各镇街常住人口排名前 5"})
    assert response.status_code == 200
    assert response.json()["data"]["session_id"] is None
    assert response.json()["data"]["message_id"] is None
    assert _count(database_path, ChatSession) == 0
    assert _count(database_path, ChatMessage) == 0


def test_authenticated_user_persists_session_and_messages(
    seeded: tuple[TestClient, Path],
) -> None:
    client, database_path = seeded
    user_id = create_user(
        database_path,
        username="aiviewer",
        password="Password1234",
        role="viewer",
        display_name="AI 用户",
    )
    token = login_token(client, "aiviewer", "Password1234")
    headers = bearer(token)

    first = client.post(
        f"{API}/ai/chat",
        headers=headers,
        json={"question": "2025 年各镇街常住人口排名前 5"},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["session_id"] is not None
    assert first_data["message_id"] is not None
    assert first_data["answer_id"].startswith("ans_")

    second = client.post(
        f"{API}/ai/chat",
        headers=headers,
        json={
            "session_id": first_data["session_id"],
            "question": "比较曲溪街道和云路镇常住人口",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["session_id"] == first_data["session_id"]

    sessions = client.get(f"{API}/ai/sessions", headers=headers).json()["data"]
    assert len(sessions) == 1
    assert sessions[0]["message_count"] == 4

    messages = client.get(
        f"{API}/ai/sessions/{first_data['session_id']}/messages",
        headers=headers,
    ).json()["data"]
    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[1]["answer_id"] == first_data["answer_id"]

    audits = _audits(database_path, "ai.chat")
    assert len(audits) == 2
    assert audits[0].user_id == user_id
    assert audits[0].detail is not None
    assert audits[0].detail["question"] == "2025 年各镇街常住人口排名前 5"


def test_other_user_cannot_read_session(
    seeded: tuple[TestClient, Path],
) -> None:
    client, database_path = seeded
    create_user(
        database_path,
        username="owner",
        password="Password1234",
        role="viewer",
    )
    create_user(
        database_path,
        username="intruder",
        password="Password1234",
        role="viewer",
    )
    owner_token = login_token(client, "owner", "Password1234")
    intruder_token = login_token(client, "intruder", "Password1234")
    created = client.post(
        f"{API}/ai/chat",
        headers=bearer(owner_token),
        json={"question": "2025 年各镇街常住人口排名前 5"},
    ).json()["data"]
    response = client.get(
        f"{API}/ai/sessions/{created['session_id']}/messages",
        headers=bearer(intruder_token),
    )
    assert response.status_code == 404


def test_guest_rate_limit_returns_429(seeded: tuple[TestClient, Path]) -> None:
    client, _ = seeded
    for _ in range(5):
        response = client.post(f"{API}/ai/chat", json={"question": "火星基地常住人口"})
        assert response.status_code == 200
    blocked = client.post(f"{API}/ai/chat", json={"question": "火星基地常住人口"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def _llm_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, handler: Any) -> TestClient:
    database_path = tmp_path / "llm.db"
    sync_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(alembic_config(sync_url), "head")
    import asyncio

    asyncio.run(seed_demo(sync_url))
    app = create_app(
        settings=Settings(
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            jwt_secret=SecretStr(TEST_JWT_SECRET),
            llm_api_key=SecretStr("test-key"),
            llm_base_url="https://llm.invalid/v1",
            llm_model="mock-model",
        )
    )

    def factory(timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr("app.ai.llm.build_http_client", factory)
    return TestClient(app)


def _mock_answer_content() -> str:
    citation = {
        "id": "c1",
        "citation_id": "c1",
        "indicator": "常住人口",
        "indicator_code": "population_resident",
        "region": "云路镇",
        "region_code": "JD-T-02",
        "region_name": "云路镇",
        "region_level": "town",
        "period": "2025",
        "source": "data_values",
        "data_as_of": "2026-11-10",
    }
    return json.dumps(
        {
            "answer_markdown": "2025 年云路镇常住人口为示例工具值。",
            "intent": "lookup",
            "blocks": [
                {
                    "id": "b1",
                    "type": "summary",
                    "component": "text",
                    "props": {},
                    "text": "2025 年云路镇常住人口为示例工具值。",
                },
                {
                    "id": "b2",
                    "type": "source",
                    "component": "source_card",
                    "props": {},
                    "citations": [citation],
                },
            ],
            "citations": [citation],
            "actions": [],
            "follow_up_questions": [],
            "status": "done",
        },
        ensure_ascii=False,
    )


def test_mocked_llm_returns_valid_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": _mock_answer_content()}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            },
        )

    client = _llm_client(tmp_path, monkeypatch, handler)
    with client:
        response = client.post(f"{API}/ai/chat", json={"question": "2025 年云路镇常住人口"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["degraded"] is False
    assert data["meta"]["model"] == "mock-model"
    assert [block["type"] for block in data["blocks"]] == ["summary", "source"]
    assert calls["count"] == 1


def test_invalid_llm_json_falls_back_to_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = _llm_client(tmp_path, monkeypatch, handler)
    with client:
        response = client.post(
            f"{API}/ai/chat",
            json={"question": "2025 年各镇街常住人口排名前 5"},
        )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["degraded"] is True
    assert data["meta"]["model"] == "deterministic-v0"
    assert "ranking" in [block["type"] for block in data["blocks"]]
    assert calls["count"] == 2
