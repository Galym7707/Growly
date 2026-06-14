from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ConversationHandler

from app.bot import handlers
from app.bot.keyboards import (
    create_post_menu_keyboard,
    main_menu_keyboard,
    more_menu_keyboard,
    sources_menu_keyboard,
)
from app.bot.states import BotState
from app.services.content_types import normalize_content_type


def keyboard_labels(markup: object) -> list[list[str]]:
    return [
        [button.text for button in row]
        for row in markup.keyboard  # type: ignore[attr-defined]
    ]


def test_main_menu_contains_only_primary_workflows() -> None:
    assert keyboard_labels(main_menu_keyboard()) == [
        ["Market scan", "Content plan"],
        ["Create post", "Sources"],
        ["Drafts", "Reports"],
        ["More"],
    ]


def test_submenus_match_mvp_structure() -> None:
    assert keyboard_labels(sources_menu_keyboard()) == [
        ["View sources"],
        ["Discover sources", "Monitor sources"],
        ["Back"],
    ]
    assert keyboard_labels(create_post_menu_keyboard()) == [
        ["Promo post", "Educational post"],
        ["Case post", "FAQ post"],
        ["News post", "Custom post"],
        ["Back"],
    ]
    assert keyboard_labels(more_menu_keyboard()) == [
        ["Web search", "Review analysis"],
        ["Sync Notion", "Settings"],
        ["Help"],
        ["Back"],
    ]


@pytest.mark.parametrize(
    ("label", "key", "prompt_name"),
    [
        ("Promo post", "promo_post", "promo_post.md"),
        ("Educational post", "educational_post", "educational_post.md"),
        ("Case post", "case_post", "case_post.md"),
        ("FAQ post", "faq_post", "faq_post.md"),
        ("News post", "news_post", "news_post.md"),
    ],
)
def test_post_menu_types_resolve_to_real_prompts(
    label: str,
    key: str,
    prompt_name: str,
) -> None:
    spec = normalize_content_type(label)
    assert spec.key == key
    assert spec.prompt_name == prompt_name


@pytest.mark.asyncio
async def test_selected_post_type_is_added_to_generation_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        text="FAQ post",
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(user_data={})

    state = await handlers.create_post_type_start(update, context)

    assert state == BotState.WAITING_POST
    assert context.user_data["post_type"] == "faq_post"

    captured: dict[str, object] = {}

    class FakeDraftService:
        async def create_post(self, payload: dict[str, object]) -> object:
            captured.update(payload)
            return SimpleNamespace(id=1)

    async def ignore_send_draft(*args: object) -> None:
        return None

    monkeypatch.setattr(handlers, "DraftService", FakeDraftService)
    monkeypatch.setattr(handlers, "send_draft", ignore_send_draft)
    message.text = "Вопросы клиентов и подтверждённые ответы."

    result = await handlers.create_post_finish(update, context)

    assert result == ConversationHandler.END
    assert str(captured["brief"]).startswith("Content type: faq_post\n")
    assert "post_type" not in context.user_data
