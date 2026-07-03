"""WhatsApp group publishing through Green API.

Green API (https://green-api.com) links a regular WhatsApp account by QR code
and exposes an HTTP API. The free "Developer" plan is enough for autoposting
into a single group chat, which the paid WhatsApp Business Cloud API does not
support at all (Cloud API cannot post to groups).

Required environment variables:
- GREEN_API_INSTANCE_ID  - the instance number, e.g. 1101123456
- GREEN_API_TOKEN        - the instance API token
- WHATSAPP_GROUP_CHAT_ID - target group id, e.g. 120363012345678901@g.us
- GREEN_API_BASE_URL     - optional, defaults to https://api.green-api.com
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.utils.errors import GrowlyError

logger = logging.getLogger(__name__)

WHATSAPP_REQUEST_TIMEOUT_SECONDS = 30.0
WHATSAPP_MAX_MESSAGE_CHARS = 4096


class WhatsAppServiceError(GrowlyError):
    """Raised when the Green API rejects or fails a request."""


class WhatsAppService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        token = self.settings.green_api_token
        return bool(
            (self.settings.green_api_instance_id or "").strip()
            and token
            and token.get_secret_value().strip()
            and (self.settings.whatsapp_group_chat_id or "").strip()
        )

    def _endpoint(self, method: str) -> str:
        base = (self.settings.green_api_base_url or "https://api.green-api.com").rstrip("/")
        instance = (self.settings.green_api_instance_id or "").strip()
        token = self.settings.green_api_token.get_secret_value().strip()
        return f"{base}/waInstance{instance}/{method}/{token}"

    async def send_text(
        self,
        text: str,
        chat_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a text message to the configured WhatsApp group.

        Returns {"message_id": ...} on success.
        """
        if not self.is_configured():
            raise WhatsAppServiceError(
                "WhatsApp не подключён. Укажите GREEN_API_INSTANCE_ID, "
                "GREEN_API_TOKEN и WHATSAPP_GROUP_CHAT_ID."
            )
        target = (chat_id or self.settings.whatsapp_group_chat_id or "").strip()
        message = (text or "").strip()[:WHATSAPP_MAX_MESSAGE_CHARS]
        if not message:
            raise WhatsAppServiceError("Пустое сообщение нельзя отправить в WhatsApp.")
        try:
            async with httpx.AsyncClient(
                timeout=WHATSAPP_REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    self._endpoint("sendMessage"),
                    json={"chatId": target, "message": message},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise WhatsAppServiceError(
                "WhatsApp (Green API) недоступен. Попробуйте позже."
            ) from exc
        if response.status_code != 200:
            logger.warning(
                "Green API sendMessage failed with status %s",
                response.status_code,
            )
            raise WhatsAppServiceError(
                f"WhatsApp (Green API) вернул статус {response.status_code}. "
                "Проверьте инстанс и токен в личном кабинете green-api.com."
            )
        payload: dict[str, Any] = {}
        try:
            payload = response.json()
        except ValueError:
            pass
        message_id = str(payload.get("idMessage") or "").strip()
        if not message_id:
            raise WhatsAppServiceError(
                "WhatsApp (Green API) не вернул идентификатор сообщения."
            )
        return {"message_id": message_id}

    async def instance_state(self) -> str:
        """Return the Green API instance state (authorized, notAuthorized, ...)."""
        if not self.is_configured():
            return "not_configured"
        try:
            async with httpx.AsyncClient(
                timeout=WHATSAPP_REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(self._endpoint("getStateInstance"))
            if response.status_code != 200:
                return f"error_{response.status_code}"
            return str(response.json().get("stateInstance") or "unknown")
        except (httpx.HTTPError, ValueError):
            return "unreachable"
