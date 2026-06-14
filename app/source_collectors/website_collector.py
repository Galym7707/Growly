from __future__ import annotations

from typing import Any

from app.source_collectors.base import CollectedItem, SourceCollector


class WebsiteCollector(SourceCollector):
    async def collect(self, **kwargs: Any) -> list[CollectedItem]:
        raise NotImplementedError(
            "Automated website collection is disabled in v1. "
            "Add public content manually after confirming permission and applicable terms."
        )

