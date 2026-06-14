from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class CollectedItem:
    title: str | None
    raw_text: str
    external_url: str | None = None
    published_at: datetime | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class SourceCollector(ABC):
    @abstractmethod
    async def collect(self, **kwargs: Any) -> list[CollectedItem]:
        raise NotImplementedError

