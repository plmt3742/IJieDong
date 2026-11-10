"""Unit tests for the in-memory AI rate limiter."""
from __future__ import annotations

import pytest

from app.ai.rate_limit import enforce_ai_rate_limit, reset_rate_limits
from app.core.config import Settings
from app.core.errors import AppError


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_rate_limits()


def _settings(**overrides: object) -> Settings:
    values = {
        "app_env": "test",
        "ai_rate_limit_per_minute": 2,
        "ai_guest_daily_limit": 2,
    }
    values.update(overrides)
    return Settings(**values)


def test_authenticated_user_is_limited_per_minute() -> None:
    settings = _settings()
    enforce_ai_rate_limit(settings=settings, user_id=1, ip="1.1.1.1")
    enforce_ai_rate_limit(settings=settings, user_id=1, ip="1.1.1.1")
    with pytest.raises(AppError) as error:
        enforce_ai_rate_limit(settings=settings, user_id=1, ip="1.1.1.1")
    assert error.value.code == "RATE_LIMITED"
    assert error.value.status_code == 429


def test_guest_is_limited_per_day_per_ip() -> None:
    settings = _settings()
    enforce_ai_rate_limit(settings=settings, user_id=None, ip="2.2.2.2")
    enforce_ai_rate_limit(settings=settings, user_id=None, ip="2.2.2.2")
    with pytest.raises(AppError) as error:
        enforce_ai_rate_limit(settings=settings, user_id=None, ip="2.2.2.2")
    assert error.value.code == "RATE_LIMITED"
    enforce_ai_rate_limit(settings=settings, user_id=None, ip="3.3.3.3")


def test_reset_clears_buckets() -> None:
    settings = _settings()
    enforce_ai_rate_limit(settings=settings, user_id=9, ip=None)
    enforce_ai_rate_limit(settings=settings, user_id=9, ip=None)
    with pytest.raises(AppError):
        enforce_ai_rate_limit(settings=settings, user_id=9, ip=None)
    reset_rate_limits()
    enforce_ai_rate_limit(settings=settings, user_id=9, ip=None)
