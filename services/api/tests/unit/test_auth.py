"""Unit tests for password hashing, JWTs, and phone masking."""
from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.core.config import DEV_JWT_SECRET, Settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    generate_status_token,
    hash_password,
    hash_status_token,
    is_strong_password,
    mask_phone,
    verify_password,
)

PASSWORD = "Passw0rd123"


def test_password_hash_uses_scrypt_with_salt_and_verifies() -> None:
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert first.startswith("scrypt$")
    assert PASSWORD not in first
    assert first != second
    assert verify_password(PASSWORD, first)
    assert verify_password(PASSWORD, second)
    assert not verify_password("WrongPassword1", first)


def test_verify_password_rejects_missing_or_malformed_hash() -> None:
    assert not verify_password(PASSWORD, None)
    assert not verify_password(PASSWORD, "")
    assert not verify_password(PASSWORD, "md5$deadbeef")
    assert not verify_password(PASSWORD, "scrypt$not-a-number$8$1$00$00")


def test_password_strength_requires_letters_digits_and_length() -> None:
    assert is_strong_password("Passw0rd12")
    assert not is_strong_password("short1")
    assert not is_strong_password("onlyletters")
    assert not is_strong_password("1234567890")


def _settings() -> Settings:
    return Settings(
        app_env="test",
        jwt_secret=SecretStr("unit-test-secret-0123456789abcdef0123456789"),
    )


def test_token_round_trip_carries_subject_role_and_version() -> None:
    token, expires_in = create_access_token(
        user_id=42,
        role="editor",
        token_version=3,
        settings=_settings(),
    )

    payload = decode_access_token(token, _settings())

    assert payload.user_id == 42
    assert payload.role == "editor"
    assert payload.token_version == 3
    assert expires_in == 480 * 60


def test_expired_token_is_rejected() -> None:
    token, _ = create_access_token(
        user_id=1,
        role="viewer",
        token_version=1,
        settings=_settings(),
        expires_minutes=-1,
    )

    with pytest.raises(TokenError):
        decode_access_token(token, _settings())


def test_token_signed_with_other_secret_is_rejected() -> None:
    token, _ = create_access_token(
        user_id=1,
        role="viewer",
        token_version=1,
        settings=_settings(),
    )
    other = Settings(
        app_env="test",
        jwt_secret=SecretStr("another-secret-0123456789abcdef0123456789"),
    )

    with pytest.raises(TokenError):
        decode_access_token(token, other)


def test_dev_settings_fall_back_to_marked_secret() -> None:
    settings = Settings(app_env="development", jwt_secret=None)

    assert settings.jwt_secret_value == DEV_JWT_SECRET


def test_production_settings_require_explicit_secret() -> None:
    settings = Settings(app_env="production", jwt_secret=None)

    with pytest.raises(RuntimeError):
        settings.validate_security()


def test_mask_phone_hides_middle_digits() -> None:
    assert mask_phone("13800008000") == "138****8000"
    assert mask_phone(None) is None
    assert mask_phone("123") == "***"


def test_status_token_is_random_and_stored_hashed() -> None:
    token = generate_status_token()
    digest = hash_status_token(token)

    assert token != digest
    assert len(digest) == 64
    assert digest == hash_status_token(token)
    assert digest != hash_status_token(generate_status_token())
