"""Tests for the health and readiness endpoints."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    request_id = response.headers["X-Request-ID"]
    assert request_id
    assert body["meta"]["request_id"] == request_id


def test_health_uses_incoming_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert response.json()["meta"]["request_id"] == "test-request-id"


def test_versioned_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_ready_returns_ready_with_sqlite(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ready"
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]


class _FailingSession:
    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("database unavailable")


async def _failing_db() -> AsyncIterator[_FailingSession]:
    yield _FailingSession()


def test_ready_returns_503_when_database_fails(app: FastAPI) -> None:
    app.dependency_overrides[get_db] = _failing_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "NOT_READY"
    assert body["request_id"] == response.headers["X-Request-ID"]
