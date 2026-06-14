from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.search.tavily_search import TavilySearchProvider
from app.utils.errors import SearchConfigurationError, SearchServiceError


def main() -> int:
    settings = get_settings()
    try:
        provider = TavilySearchProvider(settings=settings)
        results = provider.search(
            "AI content marketing automation for small business",
            max_results=3,
            search_depth="basic",
            include_raw_content=False,
        )
    except SearchConfigurationError as exc:
        print(f"FAIL: {exc}")
        return 1
    except SearchServiceError as exc:
        print(f"FAIL: {exc}")
        return 1

    print("PASS: Tavily search works")
    print(f"Results: {len(results)}")
    for result in results:
        print(f"- {result.title}")
        print(f"  {result.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
