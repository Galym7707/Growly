from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.bot.handlers as handlers


@pytest.mark.asyncio
async def test_publish_approved_collects_all_message_ids(monkeypatch) -> None:
    reservation = SimpleNamespace(
        should_publish=True,
        publication=SimpleNamespace(id=3, status="publishing"),
    )

    class FakeService:
        settings = SimpleNamespace()

        async def reserve_publication(self, draft_id):
            return reservation

        async def get(self, draft_id):
            return SimpleNamespace(id=draft_id, draft_text="hi")

        async def complete_publication(self, pub_id, message_ids):
            FakeService.completed = (pub_id, message_ids)

        async def fail_publication(self, pub_id):
            ...

    class FakeTelegram:
        def __init__(self, settings):
            ...

        async def publish_to_targets(self, bot, draft):
            return {"-100channel": [1, 2], "-100group": [3]}

    monkeypatch.setattr(handlers, "TelegramService", FakeTelegram)

    ok, msg = await handlers.publish_approved_draft(object(), FakeService(), 11)

    assert ok is True
    assert FakeService.completed[0] == 3
    assert sorted(FakeService.completed[1]) == [1, 2, 3]
