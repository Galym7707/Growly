from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.bot import handlers
from app.bot.keyboards import source_actions_keyboard


def test_source_actions_keyboard_reflects_status() -> None:
    keyboard = source_actions_keyboard(
        [
            SimpleNamespace(id=1, status="requires_review"),
            SimpleNamespace(id=2, status="active"),
            SimpleNamespace(id=3, status="disabled"),
        ]
    )
    assert keyboard is not None
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert callbacks == [
        "source:approve:1",
        "source:disable:1",
        "source:disable:2",
        "source:approve:3",
    ]


class FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.answers: list[dict[str, Any]] = []

    async def answer(self, *args: Any, **kwargs: Any) -> None:
        self.answers.append(kwargs)


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        **kwargs: Any,
    ) -> None:
        self.messages.append((chat_id, text))


@pytest.mark.asyncio
async def test_source_approve_callback_activates_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeService:
        async def approve_source(self, source_id: int) -> SimpleNamespace:
            assert source_id == 42
            return SimpleNamespace(id=42, status="active")

    monkeypatch.setattr(handlers, "SourceDiscoveryService", FakeService)
    query = FakeQuery("source:approve:42")
    context = SimpleNamespace(bot=FakeBot())
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=100, type="private"),
    )

    await handlers.source_action_callback(update, context)

    assert context.bot.messages == [
        (100, "Источник #42 подтверждён и теперь активен.")
    ]


@pytest.mark.asyncio
async def test_group_cannot_change_source_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_service() -> object:
        raise AssertionError("Group callback must not create source services.")

    monkeypatch.setattr(handlers, "SourceDiscoveryService", unexpected_service)
    query = FakeQuery("source:disable:42")
    context = SimpleNamespace(bot=FakeBot())
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=-100, type="supergroup"),
    )

    await handlers.source_action_callback(update, context)

    assert query.answers == [{"show_alert": True}]
    assert context.bot.messages == []
