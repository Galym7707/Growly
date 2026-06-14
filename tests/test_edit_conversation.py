from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.bot.handlers as handlers
from app.bot.states import BotState


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: object) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_edit_draft_finish_applies_edit_and_resends(monkeypatch) -> None:
    captured = {}

    class FakeDraftService:
        def __init__(self, *a, **k) -> None:
            pass

        async def apply_manual_edit(self, draft_id: int, text: str):
            captured["args"] = (draft_id, text)
            return SimpleNamespace(id=draft_id, version=2, status="pending")

    async def fake_send_draft(update, context, draft) -> None:
        captured["resent"] = draft.id

    monkeypatch.setattr(handlers, "DraftService", FakeDraftService)
    monkeypatch.setattr(handlers, "send_draft", fake_send_draft)

    message = FakeMessage("my corrected text")
    update = SimpleNamespace(effective_message=message, effective_chat=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"edit_draft_id": 5})

    result = await handlers.edit_draft_finish(update, context)

    assert captured["args"] == (5, "my corrected text")
    assert captured["resent"] == 5
    assert result == handlers.ConversationHandler.END
