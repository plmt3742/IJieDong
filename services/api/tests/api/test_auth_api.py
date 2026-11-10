"""API tests for login, current user, applications, and password changes."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import auth_client, bearer, create_user, login_token

PASSWORD = "Passw0rd123"


@pytest.fixture()
def api(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    with auth_client(tmp_path, filename="auth_api.db") as (client, database_path):
        create_user(
            database_path,
            username="viewer01",
            password=PASSWORD,
            role="viewer",
            phone="13800008000",
        )
        create_user(
            database_path,
            username="disabled01",
            password=PASSWORD,
            role="viewer",
            status="disabled",
            phone="13800008001",
        )
        yield client, database_path


def test_login_returns_bearer_token_and_user_summary(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer01", "password": PASSWORD},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 28800
    assert data["access_token"]
    assert data["user"]["username"] == "viewer01"
    assert data["user"]["role"] == "viewer"
    assert data["user"]["unit"] == "测试单位"
    assert data["user"]["status"] == "active"

    me = client.get("/api/v1/auth/me", headers=bearer(data["access_token"]))
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "viewer01"


@pytest.mark.parametrize(
    ("username", "password"),
    [("viewer01", "WrongPassword1"), ("missing-user", PASSWORD)],
)
def test_login_failure_uses_single_invalid_credential_code(
    api: tuple[TestClient, Path],
    username: str,
    password: str,
) -> None:
    client, _ = api
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID"


def test_disabled_user_cannot_log_in(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "disabled01", "password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_DISABLED"


def test_me_requires_valid_token(api: tuple[TestClient, Path]) -> None:
    client, _ = api

    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "AUTH_REQUIRED"

    invalid = client.get("/api/v1/auth/me", headers=bearer("not-a-jwt"))
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "AUTH_INVALID"


def test_apply_then_query_status_with_opaque_token(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    payload = {
        "display_name": "李四",
        "unit": "玉湖镇",
        "phone": "13800009000",
        "reason": "需要查询本镇指标并导出汇报卡",
        "privacy_consent": True,
    }

    response = client.post("/api/v1/auth/apply", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["application_no"].startswith("AP")
    assert len(data["status_token"]) >= 32
    assert data["submitted_at"]

    status = client.get(
        "/api/v1/auth/application-status",
        params={
            "application_no": data["application_no"],
            "status_token": data["status_token"],
        },
    )
    assert status.status_code == 200
    assert status.json()["data"]["status"] == "pending"

    wrong = client.get(
        "/api/v1/auth/application-status",
        params={
            "application_no": data["application_no"],
            "status_token": "wrong-token",
        },
    )
    assert wrong.status_code == 404
    assert wrong.json()["error"]["code"] == "NOT_FOUND"


def test_duplicate_pending_phone_is_rejected(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    payload = {
        "display_name": "王五",
        "unit": "曲溪街道",
        "phone": "13800009001",
        "reason": "需要查询本街道统计数据并核对口径",
        "privacy_consent": True,
    }

    first = client.post("/api/v1/auth/apply", json=payload)
    assert first.status_code == 200
    second = client.post("/api/v1/auth/apply", json=payload)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "APPLICATION_DUPLICATE"


def test_apply_requires_privacy_consent(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    response = client.post(
        "/api/v1/auth/apply",
        json={
            "display_name": "王五",
            "unit": "曲溪街道",
            "phone": "13800009002",
            "reason": "需要查询本街道统计数据并核对口径",
            "privacy_consent": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_change_password_invalidates_old_token(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "viewer01", PASSWORD)
    response = client.post(
        "/api/v1/auth/change-password",
        headers=bearer(token),
        json={"old_password": PASSWORD, "new_password": "NewPassw0rd1"},
    )

    assert response.status_code == 200, response.text
    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401
    assert login_token(client, "viewer01", "NewPassw0rd1")


def test_change_password_rejects_weak_new_password(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "viewer01", PASSWORD)
    response = client.post(
        "/api/v1/auth/change-password",
        headers=bearer(token),
        json={"old_password": PASSWORD, "new_password": "allletters"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_logout_returns_no_content(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    token = login_token(client, "viewer01", PASSWORD)

    response = client.post("/api/v1/auth/logout", headers=bearer(token))

    assert response.status_code == 204
    assert response.content == b""
