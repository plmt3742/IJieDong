"""API tests for application approval, user management, and audit listing."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import auth_client, bearer, create_user, login_token

PASSWORD = "Passw0rd123"


@pytest.fixture()
def api(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    with auth_client(tmp_path, filename="admin_api.db") as (client, database_path):
        create_user(
            database_path,
            username="admin01",
            password=PASSWORD,
            role="admin",
            display_name="管理员",
            phone="13700000001",
        )
        create_user(
            database_path,
            username="approver01",
            password=PASSWORD,
            role="approver",
            display_name="审批员",
            phone="13700000002",
        )
        create_user(
            database_path,
            username="viewer01",
            password=PASSWORD,
            role="viewer",
            display_name="查看者",
            phone="13700000003",
        )
        yield client, database_path


def _apply(client: TestClient, phone: str, name: str = "申请人") -> dict:
    response = client.post(
        "/api/v1/auth/apply",
        json={
            "display_name": name,
            "unit": "玉湖镇",
            "phone": phone,
            "reason": "需要查询本镇指标并导出汇报卡",
            "privacy_consent": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _find_application(client: TestClient, token: str, application_no: str) -> dict:
    response = client.get(
        "/api/v1/admin/applications",
        headers=bearer(token),
        params={"q": application_no},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total"] == 1
    return body["data"][0]


def test_approver_approves_and_created_user_can_log_in(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    approver_token = login_token(client, "approver01", PASSWORD)
    application = _apply(client, "13811110001", "李四")
    record = _find_application(client, approver_token, application["application_no"])

    response = client.post(
        f"/api/v1/admin/applications/{record['id']}/approve",
        headers=bearer(approver_token),
        json={"role": "viewer", "note": "单位核对通过"},
    )

    assert response.status_code == 200, response.text
    approved = response.json()["data"]
    assert approved["status"] == "approved"
    assert approved["role"] == "viewer"
    assert approved["username"] == "13811110001"
    assert approved["initial_password"]

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "13811110001", "password": approved["initial_password"]},
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["user"]["role"] == "viewer"

    status = client.get(
        "/api/v1/auth/application-status",
        params={
            "application_no": application["application_no"],
            "status_token": application["status_token"],
        },
    )
    assert status.json()["data"]["status"] == "approved"

    repeat = client.post(
        f"/api/v1/admin/applications/{record['id']}/approve",
        headers=bearer(approver_token),
        json={"role": "viewer"},
    )
    assert repeat.status_code == 409
    assert repeat.json()["error"]["code"] == "APPLICATION_NOT_PENDING"


def test_approver_cannot_assign_admin(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    approver_token = login_token(client, "approver01", PASSWORD)
    application = _apply(client, "13811110002")
    record = _find_application(client, approver_token, application["application_no"])

    response = client.post(
        f"/api/v1/admin/applications/{record['id']}/approve",
        headers=bearer(approver_token),
        json={"role": "admin"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    status = client.get(
        "/api/v1/auth/application-status",
        params={
            "application_no": application["application_no"],
            "status_token": application["status_token"],
        },
    )
    assert status.json()["data"]["status"] == "pending"


def test_admin_can_assign_editor(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    admin_token = login_token(client, "admin01", PASSWORD)
    application = _apply(client, "13811110003")
    record = _find_application(client, admin_token, application["application_no"])

    response = client.post(
        f"/api/v1/admin/applications/{record['id']}/approve",
        headers=bearer(admin_token),
        json={"role": "editor", "unit": "曲溪街道"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["role"] == "editor"


def test_reject_requires_reason_and_records_it(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    approver_token = login_token(client, "approver01", PASSWORD)
    application = _apply(client, "13811110004")
    record = _find_application(client, approver_token, application["application_no"])

    short = client.post(
        f"/api/v1/admin/applications/{record['id']}/reject",
        headers=bearer(approver_token),
        json={"reason": "太短"},
    )
    assert short.status_code == 422

    response = client.post(
        f"/api/v1/admin/applications/{record['id']}/reject",
        headers=bearer(approver_token),
        json={"reason": "单位信息无法核对，请补充"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "rejected"

    status = client.get(
        "/api/v1/auth/application-status",
        params={
            "application_no": application["application_no"],
            "status_token": application["status_token"],
        },
    )
    assert status.json()["data"]["reject_reason"] == "单位信息无法核对，请补充"


def test_last_active_admin_is_protected(api: tuple[TestClient, Path]) -> None:
    client, database_path = api
    admin_token = login_token(client, "admin01", PASSWORD)
    admin_id = client.get("/api/v1/auth/me", headers=bearer(admin_token)).json()["data"]["id"]

    disable = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=bearer(admin_token),
        json={"status": "disabled"},
    )
    assert disable.status_code == 409
    assert disable.json()["error"]["code"] == "LAST_ADMIN_PROTECTED"

    demote = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=bearer(admin_token),
        json={"role": "viewer"},
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "LAST_ADMIN_PROTECTED"

    create_user(
        database_path,
        username="admin02",
        password=PASSWORD,
        role="admin",
        display_name="第二管理员",
        phone="13700000004",
    )
    disable_again = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=bearer(admin_token),
        json={"status": "disabled"},
    )
    assert disable_again.status_code == 200, disable_again.text
    assert disable_again.json()["data"]["status"] == "disabled"


def test_user_list_masks_phone_and_filters_role(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    admin_token = login_token(client, "admin01", PASSWORD)

    response = client.get(
        "/api/v1/admin/users",
        headers=bearer(admin_token),
        params={"role": "viewer"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["username"] == "viewer01"
    assert body["data"][0]["phone"] == "137****0003"


def test_patch_user_writes_audit_and_invalidates_tokens(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    admin_token = login_token(client, "admin01", PASSWORD)
    viewer_token = login_token(client, "viewer01", PASSWORD)
    viewer_id = client.get("/api/v1/auth/me", headers=bearer(viewer_token)).json()["data"]["id"]

    response = client.patch(
        f"/api/v1/admin/users/{viewer_id}",
        headers=bearer(admin_token),
        json={"role": "editor", "display_name": "新查看者"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["role"] == "editor"
    assert response.json()["data"]["display_name"] == "新查看者"
    assert client.get("/api/v1/auth/me", headers=bearer(viewer_token)).status_code == 401

    audit = client.get(
        "/api/v1/admin/audit-logs",
        headers=bearer(admin_token),
        params={"action": "user.role_change"},
    )
    assert audit.status_code == 200
    assert audit.json()["meta"]["total"] == 1
    assert audit.json()["data"][0]["resource_id"] == str(viewer_id)


def test_approver_cannot_list_users(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    approver_token = login_token(client, "approver01", PASSWORD)

    response = client.get("/api/v1/admin/users", headers=bearer(approver_token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_approver_cannot_approve_own_phone(api: tuple[TestClient, Path]) -> None:
    client, database_path = api
    application = _apply(client, "13811110005")
    create_user(
        database_path,
        username="selfapprover",
        password=PASSWORD,
        role="approver",
        display_name="自批审批员",
        phone="13811110005",
    )
    token = login_token(client, "selfapprover", PASSWORD)
    record = _find_application(client, token, application["application_no"])

    response = client.post(
        f"/api/v1/admin/applications/{record['id']}/approve",
        headers=bearer(token),
        json={"role": "viewer"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_APPROVE_SELF"


def test_audit_log_filter_returns_matching_actions(api: tuple[TestClient, Path]) -> None:
    client, _ = api
    admin_token = login_token(client, "admin01", PASSWORD)
    login_token(client, "viewer01", PASSWORD)

    response = client.get(
        "/api/v1/admin/audit-logs",
        headers=bearer(admin_token),
        params={"action": "auth.login.success"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data
    assert all(item["action"] == "auth.login.success" for item in data)
    ids = [item["id"] for item in data]
    assert ids == sorted(ids, reverse=True)
