from __future__ import annotations

from typing import Any

from app.source_collectors.base import CollectedItem, SourceCollector


class TelegramPublicCollector(SourceCollector):
    async def collect(self, **kwargs: Any) -> list[CollectedItem]:
        raise NotImplementedError(
            "Automated Telegram collection is disabled in v1. "
            "Only manually supplied public content is supported."
        )

