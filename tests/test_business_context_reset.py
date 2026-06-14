from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.bot import handlers
from app.bot.keyboards import new_business_confirmation_keyboard
from app.services.business_context_service import (
    BusinessContextResetResult,
    BusinessContextService,
)


class FakeDeleteSession:
    def __init__(self) -> None:
        self.tables: list[str] = []
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> SimpleNamespace:
        self.statements.append(statement)
        self.tables.append(statement.table.name)
        return SimpleNamespace(rowcount=1)


class FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.answers: list[dict[str, Any]] = []
        self.markup_updates: list[Any] = []

    async def answer(self, **kwargs: Any) -> None:
        self.answers.append(kwargs)

    async def edit_message_reply_markup(self, reply_markup: Any) -> None:
        self.markup_updates.append(reply_markup)


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str, dict[str, Any]]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        **kwargs: Any,
    ) -> None:
        self.messages.append((chat_id, text, kwargs))


def test_reset_deletes_dependent_rows_before_parent_rows() -> None:
    session = FakeDeleteSession()

    counts = BusinessContextService._delete_rows(session)  # type: ignore[arg-type]

    assert session.tables == [
        "approvals",
        "market_scan_jobs",
        "publications",
        "drafts",
        "content_plan",
        "source_items",
        "sources",
        "reviews_imports",
        "reports",
        "settings",
    ]
    assert counts["business_settings"] == 1
    assert "business_%" in session.statements[-1].compile().params.values()


def test_new_business_keyboard_requires_explicit_confirmation() -> None:
    keyboard = new_business_confirmation_keyboard()
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert callbacks == ["business_reset:confirm", "business_reset:cancel"]


@pytest.mark.asyncio
async def test_new_business_cancel_does_not_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_service() -> object:
        raise AssertionError("Cancel must not create the reset service.")

    monkeypatch.setattr(handlers, "BusinessContextService", unexpected_service)
    query = FakeQuery("business_reset:cancel")
    context = SimpleNamespace(bot=FakeBot(), user_data={"plan": "active"})
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=100, type="private"),
    )

    await handlers.new_business_callback(update, context)

    assert context.user_data == {"plan": "active"}
    assert "Сброс отменён." in context.bot.messages[0][1]


@pytest.mark.asyncio
async def test_new_business_confirm_resets_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeService:
        async def reset(self) -> BusinessContextResetResult:
            return BusinessContextResetResult(
                deleted_counts={"source_items": 4, "reports": 2},
                notion_archived=6,
                notion_missing=0,
                notion_failed=0,
            )

    monkeypatch.setattr(handlers, "BusinessContextService", FakeService)
    query = FakeQuery("business_reset:confirm")
    context = SimpleNamespace(bot=FakeBot(), user_data={"plan": "active"})
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=100, type="private"),
    )

    await handlers.new_business_callback(update, context)

    assert context.user_data == {}
    assert any(
        "Контекст очищен." in text for _, text, _ in context.bot.messages
    )
    assert any(
        "Удалено записей из Supabase: 6." in text
        for _, text, _ in context.bot.messages
    )
