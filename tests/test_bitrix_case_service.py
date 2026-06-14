from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.bitrix_case_service import BitrixCaseService


@pytest.mark.asyncio
async def test_handle_deal_creates_case_draft_from_anonymized_data() -> None:
    seen = {}

    class FakeDraftService:
        async def create_case_post(self, context):
            seen["context"] = context
            return SimpleNamespace(id=99)

    svc = BitrixCaseService(draft_service=FakeDraftService())
    draft = await svc.handle_deal({
        "deal_id": "7",
        "category": "Авто",
        "amount": 10,
        "client_name": "Secret Name",
        "publish_amount": False,
    })

    assert draft.id == 99
    assert "client_name" not in seen["context"]
    assert seen["context"]["amount"] is None
    assert seen["context"]["category"] == "Авто"
