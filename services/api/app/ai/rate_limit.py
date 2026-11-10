"""Simple in-memory AI rate limiting for the single-process Demo v0 deployment."""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import date

from app.core.config import Settings
from app.core.errors import AppError

_LOCK = threading.Lock()
_MINUTE_BUCKETS: dict[str, deque[float]] = {}
_DAILY_BUCKETS: dict[str, tuple[date, int]] = {}


def reset_rate_limits() -> None:
    with _LOCK:
        _MINUTE_BUCKETS.clear()
        _DAILY_BUCKETS.clear()


def _consume_minute(bucket: str, limit: int, window: float = 60.0) -> bool:
    now = time.monotonic()
    entries = _MINUTE_BUCKETS.setdefault(bucket, deque())
    while entries and now - entries[0] > window:
        entries.popleft()
    if len(entries) >= limit:
        return False
    entries.append(now)
    return True


def _consume_daily(bucket: str, limit: int) -> bool:
    today = date.today()
    stored_date, count = _DAILY_BUCKETS.get(bucket, (today, 0))
    if stored_date != today:
        count = 0
    if count >= limit:
        _DAILY_BUCKETS[bucket] = (today, count)
        return False
    _DAILY_BUCKETS[bucket] = (today, count + 1)
    return True


def enforce_ai_rate_limit(
    *,
    settings: Settings,
    user_id: int | None,
    ip: str | None,
) -> None:
    """Raise ``RATE_LIMITED`` when the caller exceeds the Demo v0 budget."""
    with _LOCK:
        if user_id is not None:
            allowed = _consume_minute(f"user:{user_id}", settings.ai_rate_limit_per_minute)
            if not allowed:
                raise AppError(
                    "RATE_LIMITED",
                    "Too many AI requests, please retry later",
                    status_code=429,
                    details={"scope": "user", "window": "minute"},
                )
            return
        allowed = _consume_minute(
            f"guest-minute:{ip or 'unknown'}",
            settings.ai_rate_limit_per_minute,
        )
        if not allowed:
            raise AppError(
                "RATE_LIMITED",
                "Too many AI requests, please retry later",
                status_code=429,
                details={"scope": "guest", "window": "minute"},
            )
        allowed = _consume_daily(
            f"guest:{ip or 'unknown'}",
            settings.ai_guest_daily_limit,
        )
        if not allowed:
            raise AppError(
                "RATE_LIMITED",
                "Guest AI quota exhausted for today",
                status_code=429,
                details={"scope": "guest", "window": "day"},
            )
