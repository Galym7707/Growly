from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.bot.handlers import publish_approved_draft
from app.bot.keyboards import approved_keyboard, approval_keyboard
from app.services.telegram_service import TelegramService


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_message(self, **kwargs: object) -> SimpleNamespace:
        self.messages.append(kwargs)
        return SimpleNamespace(message_id=len(self.messages))


class FakeSettings:
    telegram_publish_chat_id = "-1001234567890"
    telegram_channel_id = "-1001234567890"

    def telegram_publish_target(self) -> str:
        return self.telegram_publish_chat_id


@pytest.mark.asyncio
async def test_long_publication_is_split_and_all_ids_are_returned() -> None:
    bot = FakeBot()
    service = TelegramService(settings=FakeSettings())
    draft = SimpleNamespace(draft_text=("A" * 3000) + "\n" + ("B" * 3000))

    message_ids = await service.publish_to_group(bot, draft)

    assert message_ids == [1, 2]
    assert len(bot.messages) == 2
    assert all(len(str(message["text"])) <= 3900 for message in bot.messages)


@pytest.mark.asyncio
async def test_duplicate_reservation_does_not_send_again() -> None:
    publication = SimpleNamespace(id=9, status="published")

    class FakeDraftService:
        async def reserve_publication(self, draft_id: int) -> SimpleNamespace:
            return SimpleNamespace(
                publication=publication,
                should_publish=False,
            )

    bot = FakeBot()
    published, result = await publish_approved_draft(
        bot,
        FakeDraftService(),  # type: ignore[arg-type]
        42,
    )

    assert published is False
    assert result == "already published"
    assert bot.messages == []


def test_publish_button_targets_telegram_group() -> None:
    keyboard = approved_keyboard(7, telegram_publish_enabled=True)
    assert keyboard is not None
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Publish to Telegram Group" in labels


def test_pending_draft_has_no_publish_button() -> None:
    keyboard = approval_keyboard(7)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Publish to Telegram Group" not in labels
