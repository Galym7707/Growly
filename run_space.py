from __future__ import annotations

import os
import threading

import uvicorn

from app.bot.bot import run_bot
from app.utils.logging import configure_logging


def run_health_server() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    configure_logging()
    health_thread = threading.Thread(
        target=run_health_server,
        name="growly-health-server",
        daemon=True,
    )
    health_thread.start()
    run_bot()
