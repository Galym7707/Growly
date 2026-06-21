from __future__ import annotations

import os

import uvicorn

from app.utils.logging import configure_logging
from scripts.init_db import main as initialize_database


def database_migrations_enabled() -> bool:
    value = os.getenv("RUN_DATABASE_MIGRATIONS", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def prepare_database() -> None:
    if not os.getenv("DATABASE_URL") or not database_migrations_enabled():
        return
    if initialize_database() != 0:
        raise RuntimeError("Database initialization failed.")


def run_web_server() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
    )


if __name__ == "__main__":
    configure_logging()
    prepare_database()
    run_web_server()
