"""Shared helpers for the B05 authentication, admin, and import API tests."""
from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.main import create_app
from app.models import User
from scripts.seed_demo import seed_demo

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = API_ROOT / "alembic.ini"
ALEMBIC_SCRIPTS = API_ROOT / "alembic"
TEST_JWT_SECRET = "test-only-jwt-secret-0123456789abcdef0123456789"


def alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def create_user(
    database_path: Path,
    *,
    username: str,
    password: str,
    role: str = "viewer",
    status: str = "active",
    display_name: str | None = None,
    unit: str | None = "测试单位",
    phone: str | None = None,
) -> int:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with Session(engine) as session:
            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name or username,
                role=role,
                status=status,
                unit=unit,
                phone=phone or f"139{abs(hash(username)) % 10**8:08d}",
                must_change_password=False,
                token_version=1,
            )
            session.add(user)
            session.commit()
            return user.id
    finally:
        engine.dispose()


@contextmanager
def auth_client(
    tmp_path: Path,
    *,
    seeded: bool = False,
    filename: str = "auth.db",
) -> Iterator[tuple[TestClient, Path]]:
    database_path = tmp_path / filename
    sync_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(alembic_config(sync_url), "head")
    if seeded:
        asyncio.run(seed_demo(sync_url))

    app = create_app(
        settings=Settings(
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            jwt_secret=SecretStr(TEST_JWT_SECRET),
            llm_provider=None,
            llm_api_key=None,
            llm_base_url=None,
            llm_model=None,
        )
    )
    with TestClient(app) as client:
        yield client, database_path


def login_token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
