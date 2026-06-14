from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.bot import handlers
from app.bot.keyboards import market_scan_pending_keyboard
from app.models import SourceItem
from app.services import market_intelligence
from app.services.market_intelligence import MarketIntelligenceService
from app.utils.errors import SearchServiceError


class FakeMessage:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.messages.append((text, kwargs))


class FakeTask:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def test_pending_keyboard_has_recovery_actions() -> None:
    keyboard = market_scan_pending_keyboard(17)
    buttons = {
        button.text: button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    }

    assert buttons == {
        "Повторить ИИ-анализ": "market:retry:17",
        "Открыть источники": "market:view_sources:17",
        "Синхронизировать с Notion": "market:notion:17",
        "Создать план по доступным данным": "market:limited_plan:17",
    }


@pytest.mark.asyncio
async def test_cancel_clears_conversation_and_cancels_background_task() -> None:
    task = FakeTask()
    message = FakeMessage()
    context = SimpleNamespace(
        user_data={"market_scan": {"niche": "test"}},
        bot_data={
            "market_scan_tasks": {
                123: {
                    "task": task,
                    "job_id": 9,
                }
            }
        },
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        effective_message=message,
    )

    result = await handlers.cancel(update, context)

    assert result == handlers.ConversationHandler.END
    assert context.user_data == {}
    assert task.cancelled
    assert "Запущена отмена анализа рынка" in message.messages[0][0]


@pytest.mark.asyncio
async def test_status_renders_latest_job(monkeypatch: pytest.MonkeyPatch) -> None:
    message = FakeMessage()
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace()

    async def user_id(_: object) -> int:
        return 44

    class FakeService:
        async def latest_market_scan_job(
            self,
            saved_user_id: int,
        ) -> dict[str, Any]:
            assert saved_user_id == 44
            return {
                "task_type": "market_scan",
                "status": "analysis_pending",
                "current_step": "Шаг 4/5",
                "sources_count": 33,
                "report_status": "search_saved_analysis_pending",
                "error_message": "AI timeout",
            }

    monkeypatch.setattr(handlers, "ensure_telegram_user_id", user_id)
    monkeypatch.setattr(handlers, "MarketIntelligenceService", FakeService)

    await handlers.task_status(update, context)

    text = message.messages[0][0]
    assert "Задача: анализ рынка" in text
    assert "Сохранено источников: 33" in text
    assert "Статус отчёта: источники сохранены, анализ ожидается" in text
    assert "Последняя ошибка: превышено время ожидания" in text


@pytest.mark.asyncio
async def test_groq_batch_has_hard_generation_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowGroq:
        async def analyze_market_search(
            self,
            context: dict[str, Any],
        ) -> str:
            await asyncio.sleep(0.05)
            return "{}"

    service = MarketIntelligenceService(
        search_provider=SimpleNamespace(),
        groq=SlowGroq(),  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        market_intelligence,
        "GROQ_GENERATION_TIMEOUT_SECONDS",
        0.01,
    )

    with pytest.raises(TimeoutError):
        await service._analyze_source_item_batches(
            "query",
            [
                SourceItem(
                    id=1,
                    title="Source",
                    url="https://example.com",
                    snippet="Evidence",
                )
            ],
        )


@pytest.mark.asyncio
async def test_tavily_query_timeout_stops_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowSearch:
        def search(self, *args: Any, **kwargs: Any) -> list[Any]:
            time.sleep(0.05)
            return []

    service = MarketIntelligenceService(
        search_provider=SlowSearch(),  # type: ignore[arg-type]
        groq=SimpleNamespace(),  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        market_intelligence,
        "TAVILY_QUERY_TIMEOUT_SECONDS",
        0.01,
    )

    with pytest.raises(SearchServiceError):
        await service.run_market_scan(
            niche="test",
            region_language="test",
            competitor_keywords="none",
        )


@pytest.mark.asyncio
async def test_notion_operation_timeout_does_not_block_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowNotion:
        async def sync_source_item(
            self,
            item: SourceItem,
        ) -> dict[str, str]:
            await asyncio.sleep(0.05)
            return {"id": "page"}

    service = MarketIntelligenceService(
        search_provider=SimpleNamespace(),
        groq=SimpleNamespace(),  # type: ignore[arg-type]
        notion=SlowNotion(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        market_intelligence,
        "NOTION_OPERATION_TIMEOUT_SECONDS",
        0.01,
    )

    await asyncio.wait_for(
        service._sync_source_items(
            [
                SourceItem(
                    id=1,
                    title="Source",
                    url="https://example.com",
                    snippet="Evidence",
                )
            ]
        ),
        timeout=0.1,
    )
