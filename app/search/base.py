from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str | None
    content: str | None
    source_provider: str
    query: str
    published_at: str | None
    score: float | None
    raw_json: dict[str, Any] | None


class BaseSearchProvider(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        raise NotImplementedError
