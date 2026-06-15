from __future__ import annotations

import pytest

from app.services.content_types import CONTENT_TYPE_BY_KEY
from app.services.draft_service import DraftService


def test_instagram_caption_type_registered() -> None:
    assert "instagram_caption" in CONTENT_TYPE_BY_KEY
    assert CONTENT_TYPE_BY_KEY["instagram_caption"].prompt_name == "instagram_caption.md"


@pytest.mark.asyncio
async def test_create_instagram_caption_uses_instagram_channel(monkeypatch) -> None:
    captured = {}

    service = DraftService.__new__(DraftService)

    async def fake_typed(context, spec, *, content_plan_id=None):
        captured["channel"] = context.get("channel")
        captured["spec"] = spec.key
        return object()

    monkeypatch.setattr(service, "_create_typed_draft", fake_typed)

    await service.create_instagram_caption({"brief": "promo for a flat swap"})

    assert captured["spec"] == "instagram_caption"
    assert captured["channel"] == "Instagram"
