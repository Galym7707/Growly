"""Initialize the schema without crashing the web process during an outage."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI

from scripts.init_db import apply_migrations

logger = logging.getLogger(__name__)
DATABASE_RETRY_SECONDS = 30


def migrations_enabled() -> bool:
    # run_space enables migrations; ordinary API/test imports do not run DDL.
    return os.getenv("RUN_DATABASE_MIGRATIONS", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


async def initialize_database(app: FastAPI) -> None:
    while True:
        try:
            await asyncio.to_thread(apply_migrations)
        except Exception as exc:
            # Connection errors can contain credentials. Log only their type.
            logger.warning(
                "Database startup is unavailable (%s); retrying in %s seconds.",
                type(exc).__name__, DATABASE_RETRY_SECONDS,
            )
            await asyncio.sleep(DATABASE_RETRY_SECONDS)
        else:
            app.state.database_initializing = False
            logger.info("Database schema is ready.")
            return


@asynccontextmanager
async def database_lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_initializing = migrations_enabled()
    task = None
    if app.state.database_initializing:
        task = asyncio.create_task(initialize_database(app))
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        app.state.database_initializing = False
