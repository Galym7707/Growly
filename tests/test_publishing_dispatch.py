from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.publishing_service import PublishingService


@pytest.mark.asyncio
async def test_dispatch_publishes_due_and_completes(monkeypatch) -> None:
    due = [SimpleNamespace(id=1, draft_id=10, status="scheduled")]
    completed: list[int] = []

    svc = PublishingService.__new__(PublishingService)
    svc.settings = SimpleNamespace()

    monkeypatch.setattr(svc, "_load_due", lambda now: due)

    async def fake_publish(bot, publication):
        completed.append(publication.id)
        return True

    monkeypatch.setattr(svc, "_publish_one", fake_publish)

    count = await svc.dispatch_due(bot=object())
    assert count == 1
    assert completed == [1]
