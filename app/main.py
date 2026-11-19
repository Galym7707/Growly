from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as DatabasePoolTimeout

from app.config import get_settings
from app.database import session_scope
from app.database_lifecycle import database_lifespan
from app.runtime_status import telegram_initialized
from app.utils.errors import (
    AIServiceError,
    GrowlyError,
    IntegrationError,
    WorkspaceAccessError,
)
from app.utils.logging import configure_logging
from app.web_api import router as web_router

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(
    title="Growly API",
    description="Backend services shared by the Growly Telegram bot and web app.",
    version="0.2.0",
    lifespan=database_lifespan,
)
app.state.database_initializing = False


def database_unavailable_response() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "База данных временно недоступна. Повторите попытку позже.",
            "code": "database_unavailable",
        },
        headers={"Retry-After": "10"},
    )


@app.middleware("http")
async def wait_for_database_startup(request: Request, call_next):
    if (
        request.app.state.database_initializing
        and request.url.path.startswith("/api/")
        and request.url.path != "/api/health"
    ):
        return database_unavailable_response()
    return await call_next(request)


@app.exception_handler(OperationalError)
@app.exception_handler(DatabasePoolTimeout)
async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    del request
    logger.warning("Database request is unavailable (%s).", type(exc).__name__)
    return database_unavailable_response()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_web_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Growly-API-Key"],
)
app.include_router(web_router)


@app.exception_handler(WorkspaceAccessError)
async def workspace_access_error_handler(
    request: Request,
    exc: WorkspaceAccessError,
) -> JSONResponse:
    del request
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


@app.exception_handler(GrowlyError)
async def growly_error_handler(
    request: Request,
    exc: GrowlyError,
) -> JSONResponse:
    del request
    status_code = _growly_error_status(exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": _growly_error_detail(exc)},
    )


def _growly_error_status(exc: GrowlyError) -> int:
    if isinstance(exc, AIServiceError):
        status = getattr(exc, "status", None)
        if isinstance(status, int) and 400 <= status < 600:
            return status
        return 503
    if isinstance(exc, IntegrationError):
        status = getattr(exc, "status", None)
        if isinstance(status, int) and 400 <= status < 600:
            return status
        return 502
    return 400


def _growly_error_detail(exc: GrowlyError) -> str:
    if isinstance(exc, AIServiceError):
        if exc.is_rate_limited:
            return (
                "Генерация временно недоступна: лимит AI-сервиса исчерпан. "
                "Попробуйте позже."
            )
        return "Генерация временно недоступна. Попробуйте позже."
    return str(exc)


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request,
    exc: ValueError,
) -> JSONResponse:
    del request
    return JSONResponse(status_code=400, content={"detail": str(exc)})

from app.api.bitrix_webhook import router as bitrix_router

app.include_router(bitrix_router)


@app.get("/", include_in_schema=False)
async def root_health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "telegram": (
            "initialized"
            if telegram_initialized.is_set()
            else "initializing"
        ),
    }


@app.get("/ready", response_model=None)
async def ready() -> dict[str, str] | JSONResponse:
    if app.state.database_initializing:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "initializing"},
            headers={"Retry-After": "10"},
        )

    def check_database() -> None:
        with session_scope() as session:
            session.execute(text("SELECT 1"))

    await asyncio.to_thread(check_database)
    return {"status": "ready", "database": "connected"}
