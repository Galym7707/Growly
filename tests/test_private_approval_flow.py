from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.bot import handlers


class FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.answers: list[dict[str, object]] = []
        self.reply_markup_updates: list[object] = []

    async def answer(self, *args: object, **kwargs: object) -> None:
        self.answers.append(kwargs)

    async def edit_message_reply_markup(self, reply_markup: object) -> None:
        self.reply_markup_updates.append(reply_markup)


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


@pytest.mark.asyncio
async def test_approve_does_not_publish_automatically(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeSettings:
        def telegram_publish_target(self) -> str:
            return "-1001234567890"

    class FakeService:
        settings = FakeSettings()

        async def record_action(self, **kwargs: object) -> SimpleNamespace:
            events.append("approved")
            return SimpleNamespace(status="approved")

    async def unexpected_publish(*args: object, **kwargs: object) -> tuple[bool, str]:
        events.append("published")
        raise AssertionError("Approve must not publish automatically.")

    monkeypatch.setattr(handlers, "DraftService", lambda: FakeService())
    monkeypatch.setattr(handlers, "publish_approved_draft", unexpected_publish)

    query = FakeQuery("approve:42")
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=100, type="private"),
        effective_user=SimpleNamespace(full_name="Tester"),
    )
    context = SimpleNamespace(bot=FakeBot())

    await handlers.approval_callback(update, context)

    assert events == ["approved"]
    assert context.bot.messages == [(100, "Черновик #42 одобрен.")]
    assert query.reply_markup_updates


@pytest.mark.asyncio
async def test_group_callback_cannot_control_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_service() -> object:
        raise AssertionError("Group callback must not construct management services.")

    monkeypatch.setattr(handlers, "DraftService", unexpected_service)
    query = FakeQuery("approve:42")
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=-100123, type="supergroup"),
        effective_user=SimpleNamespace(full_name="Subscriber"),
    )
    context = SimpleNamespace(bot=FakeBot())

    await handlers.approval_callback(update, context)

    assert query.answers == [{"show_alert": True}]
    assert context.bot.messages == []
