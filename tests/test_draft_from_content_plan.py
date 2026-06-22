from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.models import ContentPlan
from app.services.draft_service import DraftService


@pytest.mark.asyncio
async def test_create_from_plan_serializes_publish_date(monkeypatch) -> None:
    publish_date = datetime(2026, 6, 22, 9, 30, tzinfo=UTC)
    item = SimpleNamespace(
        id=51,
        publish_date=publish_date,
        channel="instagram",
        content_type="post",
        topic="Delivery guide",
        goal="Generate leads",
        target_audience="Small businesses",
        key_message="Reliable delivery",
        cta="Request a quote",
        source_idea="Market report",
        why_recommended="High demand",
        status="draft",
    )

    class FakeSession:
        def get(self, model, item_id):
            assert model is ContentPlan
            assert item_id == 51
            return item

    @contextmanager
    def fake_session_scope():
        yield FakeSession()

    captured: dict[str, object] = {}

    async def fake_create(context, spec, *, content_plan_id=None):
        del spec
        captured["context"] = context
        captured["content_plan_id"] = content_plan_id
        return SimpleNamespace(id=101)

    service = DraftService.__new__(DraftService)
    monkeypatch.setattr("app.services.draft_service.session_scope", fake_session_scope)
    monkeypatch.setattr(service, "_create_typed_draft", fake_create)

    draft = await service.create_from_plan(51)

    content_plan = captured["context"]["content_plan"]
    assert content_plan["publish_date"] == publish_date.isoformat()
    assert captured["content_plan_id"] == 51
    assert draft.id == 101
    assert item.status == "drafted"
