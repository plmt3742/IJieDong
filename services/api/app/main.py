"""FastAPI application factory for the i揭东 API."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_id import RequestIDMiddleware
from app.db.session import create_engine_and_sessionmaker

API_TITLE = "i揭东 API"
API_VERSION = "0.1.0"

_SAFE_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application instance."""
    resolved_settings = settings or get_settings()
    resolved_settings.validate_security()
    configure_logging(resolved_settings.log_level)

    engine, sessionmaker = create_engine_and_sessionmaker(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker

    origins = resolved_settings.cors_origin_list
    if origins:
        development = resolved_settings.is_development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"] if development else _SAFE_METHODS,
            allow_headers=(
                ["*"]
                if development
                else ["Authorization", "Content-Type", resolved_settings.request_id_header]
            ),
        )

    app.add_middleware(
        RequestIDMiddleware,
        header_name=resolved_settings.request_id_header,
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
