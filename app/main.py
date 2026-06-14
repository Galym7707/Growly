from __future__ import annotations

import asyncio

from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.database import session_scope
from app.utils.logging import configure_logging

configure_logging()
settings = get_settings()
app = FastAPI(
    title="Growly API",
    description="Backend services for Growly automation. No custom frontend is included.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/ready")
async def ready() -> dict[str, str]:
    def check_database() -> None:
        with session_scope() as session:
            session.execute(text("SELECT 1"))

    await asyncio.to_thread(check_database)
    return {"status": "ready", "database": "connected"}

