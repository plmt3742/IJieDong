"""Application settings loaded from environment variables and ``.env``."""
from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Clearly marked development-only fallback. Production/test deployments must set
# JWT_SECRET explicitly; ``validate_security`` refuses to start without it.
DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-do-not-use-in-production"


class Settings(BaseSettings):
    """Runtime configuration for the API service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    cors_origins: str = ""
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"

    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = 20.0

    # AI agent budgets (see docs/agent/24 section 6.2).
    ai_max_tool_calls: int = 5
    ai_timeout_seconds: float = 30.0
    ai_rate_limit_per_minute: int = 10
    ai_guest_daily_limit: int = 5

    # Export storage and limits (see docs/agent/25 section 6.6).
    export_dir: str = "./data/exports"
    export_retention_days: int = 7
    export_max_rows: int = 100
    export_renderer_version: str = "1.0.0"
    export_registry_version: str = "1.0.0"

    jwt_secret: SecretStr | None = None
    access_token_expire_minutes: int = 480

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a normalised list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        """True for local/development-like environments."""
        return self.app_env.strip().lower() in {"development", "dev", "local"}

    @property
    def is_test(self) -> bool:
        return self.app_env.strip().lower() in {"test", "testing"}

    @property
    def jwt_secret_value(self) -> str:
        if self.jwt_secret is not None:
            secret = self.jwt_secret.get_secret_value().strip()
            if secret:
                return secret
        if self.is_development or self.is_test:
            return DEV_JWT_SECRET
        raise RuntimeError(
            "JWT_SECRET must be configured outside development/test environments"
        )

    def validate_security(self) -> None:
        """Fail fast when a non-development deployment has no JWT secret."""
        _ = self.jwt_secret_value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
