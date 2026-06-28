from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import session_scope
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
app = FastAPI(
    title="Growly API",
    description="Backend services shared by the Growly Telegram bot and web app.",
    version="0.2.0",
)
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


@app.get("/ready")
async def ready() -> dict[str, str]:
    def check_database() -> None:
        with session_scope() as session:
            session.execute(text("SELECT 1"))

    await asyncio.to_thread(check_database)
    return {"status": "ready", "database": "connected"}
