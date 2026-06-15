from __future__ import annotations

import logging
from typing import Any

from app.config import Settings, get_settings
from app.integrations.bitrix.client import anonymize_deal
from app.models import Draft
from app.services.draft_service import DraftService

logger = logging.getLogger(__name__)


class BitrixCaseService:
    def __init__(
        self,
        settings: Settings | None = None,
        draft_service: DraftService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.draft_service = draft_service or DraftService(self.settings)

    async def handle_deal(self, payload: dict[str, Any]) -> Draft:
        context = anonymize_deal(payload)
        context["brief"] = self._brief_from(context)
        draft = await self.draft_service.create_case_post(context)
        logger.info("bitrix_case_draft_created draft_id=%s", draft.id)
        return draft

    @staticmethod
    def _brief_from(context: dict[str, Any]) -> str:
        parts = [
            f"Категория: {context.get('category') or 'не указана'}",
            f"Город: {context.get('city') or 'не указан'}",
            f"Тип актива: {context.get('asset_type') or 'не указан'}",
            f"Результат сделки: {context.get('result') or 'закрыта'}",
        ]
        if context.get("amount") is not None:
            parts.append(f"Сумма: {context['amount']}")
        parts.append(
            "Сделать обезличенный пост-кейс в tone of voice Smart Barter, "
            "без гарантий результата и без конфиденциальных данных."
        )
        return "\n".join(parts)
