"""Shared pytest fixtures for the API service."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_settings(tmp_path: Path) -> Settings:
    """Settings pointing at a throwaway SQLite database."""
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    return Settings(
        app_env="test",
        database_url=database_url,
        llm_provider=None,
        llm_api_key=None,
        llm_base_url=None,
        llm_model=None,
    )


@pytest.fixture()
def app(tmp_path: Path) -> FastAPI:
    return create_app(settings=build_settings(tmp_path))


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
