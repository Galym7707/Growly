from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from telegram.error import BadRequest

from app.bot import handlers


class ExpiredQuery:
    data = "source:approve:7"

    async def answer(self, **kwargs: Any) -> None:
        raise BadRequest(
            "Query is too old and response timeout expired or query id is invalid"
        )


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


@pytest.mark.asyncio
async def test_expired_callback_does_not_crash_or_run_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_service() -> object:
        raise AssertionError("Expired callback must not run the action.")

    monkeypatch.setattr(
        handlers,
        "SourceDiscoveryService",
        unexpected_service,
    )
    bot = FakeBot()
    update = SimpleNamespace(
        callback_query=ExpiredQuery(),
        effective_chat=SimpleNamespace(id=100, type="private"),
    )
    context = SimpleNamespace(bot=bot)

    await handlers.source_action_callback(update, context)

    assert bot.messages[0][1] == handlers.STALE_CALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_notion_sync_message_explains_empty_content_calendar() -> None:
    class FakeNotion:
        async def configured_database_links(self) -> dict[str, str]:
            return {
                "Source Items": "https://notion.so/source-items",
                "Reports": "https://notion.so/reports",
                "Content Calendar": "https://notion.so/content-calendar",
            }

    text = await handlers.format_notion_sync_result(
        FakeNotion(),  # type: ignore[arg-type]
        {
            "source_items": 25,
            "reports": 1,
            "content": 0,
            "drafts": 0,
        },
    )

    assert "Материалы источников обновлены: 25" in text
    assert "Отчёты обновлены: 1" in text
    assert "Контент-календарь обновлён: 0" in text
    assert (
        "Контент-календарь не изменился, потому что новые элементы "
        "контент-плана не были созданы."
    ) in text
    assert "https://notion.so/content-calendar" in text
