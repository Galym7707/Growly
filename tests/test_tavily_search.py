from __future__ import annotations

from typing import Any

import pytest

from app.config import Settings
from app.search.tavily_search import TavilySearchProvider
from app.utils.errors import SearchConfigurationError


class FakeTavilyClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self.payload


def test_missing_tavily_key_has_clear_error() -> None:
    settings = Settings(
        _env_file=None,
        SEARCH_PROVIDER="tavily",
        TAVILY_API_KEY=None,
    )
    with pytest.raises(
        SearchConfigurationError,
        match="Tavily is not configured",
    ):
        TavilySearchProvider(settings=settings)


def test_tavily_provider_normalizes_results_and_uses_safe_defaults() -> None:
    client = FakeTavilyClient(
        {
            "results": [
                {
                    "title": "Example",
                    "url": "https://example.com/article",
                    "content": "Public snippet",
                    "raw_content": "Raw body",
                    "published_date": "2026-05-01",
                    "score": 0.87,
                }
            ]
        }
    )
    settings = Settings(
        _env_file=None,
        SEARCH_PROVIDER="tavily",
        TAVILY_API_KEY="test-key",
        SEARCH_MAX_RESULTS=10,
        SEARCH_DEPTH="basic",
        SEARCH_SAVE_RAW=True,
    )
    provider = TavilySearchProvider(settings=settings, client=client)  # type: ignore[arg-type]

    results = provider.search("market query")

    assert len(results) == 1
    assert results[0].title == "Example"
    assert results[0].snippet == "Public snippet"
    assert results[0].content is None
    assert results[0].source_provider == "tavily"
    assert results[0].query == "market query"
    assert results[0].score == 0.87
    assert results[0].raw_json is not None
    assert client.calls == [
        {
            "query": "market query",
            "search_depth": "basic",
            "max_results": 10,
            "include_answer": False,
            "include_raw_content": False,
        }
    ]
