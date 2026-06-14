from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.notion_service import NotionService
from app.utils.logging import configure_logging


async def run() -> int:
    configure_logging()
    try:
        await NotionService().ensure_workspace()
        print(
            "Notion initialization completed. Growly Dashboard and all required "
            "databases were created or reused."
        )
        return 0
    except Exception as exc:
        print(
            "ERROR: Notion initialization failed "
            f"({type(exc).__name__}). Secret values were not printed."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

