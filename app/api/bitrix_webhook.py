from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import Settings, get_settings
from app.services.bitrix_case_service import BitrixCaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/bitrix", tags=["bitrix"])


def verify_secret(token: str | None, settings: Settings) -> None:
    if not settings.bitrix_enabled or settings.bitrix_webhook_secret is None:
        raise HTTPException(status_code=404, detail="Bitrix webhook is disabled.")
    expected = settings.bitrix_webhook_secret.get_secret_value()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook token.")


@router.post("/deal-closed")
async def deal_closed(
    request: Request,
    x_bitrix_token: str | None = Header(default=None),
) -> dict[str, Any]:
    settings = get_settings()
    verify_secret(x_bitrix_token, settings)
    payload = await request.json()
    try:
        draft = await BitrixCaseService(settings).handle_deal(payload)
    except Exception:
        logger.exception("Bitrix deal handling failed.")
        return {"status": "accepted", "draft_id": None}
    return {"status": "accepted", "draft_id": draft.id}
