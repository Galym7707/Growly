from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.database import session_scope
from app.models import Source
from app.repositories.sources_repo import SourcesRepository
from app.utils.logging import configure_logging


def main() -> int:
    configure_logging()
    try:
        with session_scope() as session:
            repo = SourcesRepository(session)
            existing = session.scalar(
                select(Source).where(Source.name == "Growly demo public source")
            )
            if existing:
                print("Demo data already exists; no duplicate rows were added.")
                return 0
            source = repo.create_source(
                name="Growly demo public source",
                source_type="manual",
                category="demo",
                notes=(
                    "Synthetic example for testing. It does not describe a real competitor."
                ),
            )
            repo.create_item(
                source_id=source.id,
                title="Synthetic weekly content sample",
                raw_text=(
                    "Synthetic test record: a fictional business published an educational "
                    "guide, a product comparison, and a short process video. No real-world "
                    "performance claims or metrics are attached."
                ),
                tags=["demo", "synthetic"],
            )
        print("Synthetic demo source and source item were added.")
        return 0
    except Exception as exc:
        print(
            f"ERROR: demo seed failed ({type(exc).__name__}). "
            "Secret values were not printed."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

