from __future__ import annotations

from typing import Any

from app.source_collectors.base import CollectedItem, SourceCollector


class ManualCollector(SourceCollector):
    async def collect(self, **kwargs: Any) -> list[CollectedItem]:
        raw_text = str(kwargs.get("raw_text", "")).strip()
        if not raw_text:
            raise ValueError("Manual source text cannot be empty.")
        return [
            CollectedItem(
                title=kwargs.get("title"),
                raw_text=raw_text,
                external_url=kwargs.get("external_url"),
                metrics=kwargs.get("metrics") or {},
                tags=kwargs.get("tags") or [],
            )
        ]

