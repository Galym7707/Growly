from __future__ import annotations

from typing import Any

from tavily import TavilyClient

from app.config import Settings, get_settings
from app.search.base import BaseSearchProvider, SearchResult
from app.utils.errors import SearchConfigurationError, SearchServiceError


class TavilySearchProvider(BaseSearchProvider):
    def __init__(
        self,
        settings: Settings | None = None,
        client: TavilyClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        try:
            api_key = self.settings.tavily_key()
        except Exception as exc:
            raise SearchConfigurationError(
                "Tavily is not configured. Add TAVILY_API_KEY to .env."
            ) from exc
        self.client = client or TavilyClient(api_key=api_key)

    def search(
        self,
        query: str,
        max_results: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        clean_query = query.strip()
        if not clean_query:
            raise SearchServiceError("Search query cannot be empty.")

        search_depth = str(
            kwargs.pop("search_depth", self.settings.search_depth) or "basic"
        ).strip().lower()
        if search_depth not in {"basic", "advanced"}:
            raise SearchConfigurationError(
                "SEARCH_DEPTH must be either 'basic' or 'advanced'."
            )
        include_raw_content = bool(kwargs.pop("include_raw_content", False))
        result_limit = max_results or self.settings.search_max_results

        try:
            payload = self.client.search(
                query=clean_query,
                search_depth=search_depth,
                max_results=result_limit,
                include_answer=False,
                include_raw_content=include_raw_content,
                **kwargs,
            )
        except Exception as exc:
            raise SearchServiceError(
                "Tavily search is temporarily unavailable. Please try again later."
            ) from exc

        rows = payload.get("results", []) if isinstance(payload, dict) else []
        normalized: list[SearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            url = str(row.get("url") or "").strip()
            if not title or not url:
                continue
            score_value = row.get("score")
            try:
                score = float(score_value) if score_value is not None else None
            except (TypeError, ValueError):
                score = None
            normalized.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=str(row.get("content") or "").strip() or None,
                    content=(
                        str(row.get("raw_content") or "").strip() or None
                        if include_raw_content
                        else None
                    ),
                    source_provider="tavily",
                    query=clean_query,
                    published_at=(
                        str(
                            row.get("published_date")
                            or row.get("published_at")
                            or ""
                        ).strip()
                        or None
                    ),
                    score=score,
                    raw_json=dict(row) if self.settings.search_save_raw else None,
                )
            )
        return normalized
