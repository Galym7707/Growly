"""Entrypoint for the HuggingFace Docker Space (runs the FastAPI web server)."""

from __future__ import annotations

import os

import uvicorn

from app.utils.logging import configure_logging


def run_web_server() -> None:
    # Keep health checks available while the API lifespan retries migrations.
    os.environ.setdefault("RUN_DATABASE_MIGRATIONS", "true")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
    )


if __name__ == "__main__":
    configure_logging()
    run_web_server()
