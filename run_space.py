from __future__ import annotations

import os

import uvicorn

from app.utils.logging import configure_logging


def run_web_server() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
    )


if __name__ == "__main__":
    configure_logging()
    run_web_server()
