from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.draft_service import DraftService


@pytest.mark.asyncio
async def test_apply_manual_edit_persists_and_syncs(monkeypatch) -> None:
    edited = SimpleNamespace(id=7, draft_text="edited", status="pending", notion_page_id="p1")

    service = DraftService.__new__(DraftService)
    service.settings = SimpleNamespace()
    synced: list[int] = []

    async def fake_to_thread(fn, *a, **k):
        return fn(*a, **k)

    async def fake_safe_sync(draft) -> None:
        synced.append(draft.id)

    monkeypatch.setattr("app.services.draft_service.asyncio.to_thread", fake_to_thread)
    monkeypatch.setattr(service, "_safe_sync", fake_safe_sync)
    monkeypatch.setattr(service, "_edit_in_session", lambda draft_id, text: edited)

    result = await service.apply_manual_edit(9, "edited")

    assert result is edited
    assert synced == [7]
