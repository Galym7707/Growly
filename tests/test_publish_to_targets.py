from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.telegram_service import TelegramService


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)
        return SimpleNamespace(message_id=len(self.sent))


class FakeSettings:
    telegram_channel_id = "-100channel"
    telegram_publish_chat_id = "-100group"
    publish_to_channel = True
    publish_to_group = True

    def telegram_publish_target(self):
        return self.telegram_publish_chat_id


@pytest.mark.asyncio
async def test_publish_to_targets_sends_to_both_when_enabled() -> None:
    svc = TelegramService(FakeSettings())
    bot = FakeBot()
    draft = SimpleNamespace(draft_text="hello world")

    result = await svc.publish_to_targets(bot, draft)

    assert set(result.keys()) == {"-100channel", "-100group"}
    chat_ids = {m["chat_id"] for m in bot.sent}
    assert chat_ids == {"-100channel", "-100group"}


@pytest.mark.asyncio
async def test_publish_to_targets_raises_when_no_destination() -> None:
    class NoDest(FakeSettings):
        publish_to_channel = False
        publish_to_group = False

    with pytest.raises(ValueError):
        await TelegramService(NoDest()).publish_to_targets(FakeBot(), SimpleNamespace(draft_text="x"))
