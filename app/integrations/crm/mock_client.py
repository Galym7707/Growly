from __future__ import annotations

from typing import Any

from app.integrations.crm.base import CRMClient


class MockCRMClient(CRMClient):
    async def create_lead(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError(
            "CRM integration is disabled. Select and configure an official provider first."
        )

