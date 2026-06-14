from __future__ import annotations

from datetime import datetime, timedelta, UTC
from types import SimpleNamespace

import pytest

from app.services.draft_service import DraftService


@pytest.mark.asyncio
async def test_schedule_publication_requires_future_time() -> None:
    service = DraftService.__new__(DraftService)
    service.settings = SimpleNamespace()
    past = datetime.now(UTC) - timedelta(minutes=1)
    with pytest.raises(ValueError):
        await service.schedule_publication(1, past)
