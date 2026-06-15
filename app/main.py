from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import session_scope
from app.runtime_status import telegram_initialized
from app.utils.errors import GrowlyError, IntegrationError
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
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Growly-API-Key"],
)
app.include_router(web_router)


@app.exception_handler(GrowlyError)
async def growly_error_handler(
    request: Request,
    exc: GrowlyError,
) -> JSONResponse:
    del request
    status_code = 502 if isinstance(exc, IntegrationError) else 400
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request,
    exc: ValueError,
) -> JSONResponse:
    del request
    return JSONResponse(status_code=400, content={"detail": str(exc)})


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
