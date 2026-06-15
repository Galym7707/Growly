from __future__ import annotations

from typing import Any

_PII_KEYS = {"client_name", "client_phone", "client_email", "manager_name", "contact"}


def anonymize_deal(payload: dict[str, Any]) -> dict[str, Any]:
    publish_amount = bool(payload.get("publish_amount", False))
    clean: dict[str, Any] = {
        "deal_id": str(payload.get("deal_id", "")).strip() or None,
        "category": payload.get("category"),
        "city": payload.get("city"),
        "asset_type": payload.get("asset_type"),
        "result": payload.get("result"),
        "amount": payload.get("amount") if publish_amount else None,
        "publish_amount": publish_amount,
    }
    return {k: v for k, v in clean.items() if k not in _PII_KEYS}


class BitrixClient:
    """Inbound-only adapter. Growly receives deal-closed webhooks; it never writes to Bitrix."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    async def send_lead(self, *_: object, **__: object) -> None:
        raise NotImplementedError("Outbound Bitrix writes are intentionally unsupported.")
