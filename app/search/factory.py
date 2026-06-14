from __future__ import annotations

from app.config import Settings, get_settings
from app.search.base import BaseSearchProvider
from app.search.tavily_search import TavilySearchProvider
from app.utils.errors import SearchConfigurationError


def get_search_provider(settings: Settings | None = None) -> BaseSearchProvider:
    settings = settings or get_settings()
    provider = (settings.search_provider or "").strip().lower()
    if not provider:
        raise SearchConfigurationError(
            "SEARCH_PROVIDER is not configured. Set SEARCH_PROVIDER=tavily in .env."
        )
    if provider == "tavily":
        return TavilySearchProvider(settings=settings)
    raise SearchConfigurationError(
        f"Unsupported SEARCH_PROVIDER: {provider}. Supported provider: tavily."
    )
