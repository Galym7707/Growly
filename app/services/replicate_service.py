"""Replicate AI-media provider.

Only the backend talks to Replicate; the frontend never receives the token.
Replicate is used as an alternative to Blotato for generating AI video (and,
optionally, images) from a text prompt. Generation is asynchronous: a
prediction is created, then polled until it succeeds or fails.

The provider contract (auth header, endpoints, status vocabulary) is kept in
the constants below so it is easy to adjust if Replicate changes it.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.utils.errors import ConfigurationError, ReplicateServiceError

logger = logging.getLogger(__name__)

REPLICATE_TIMEOUT_SECONDS = 30.0

# Map Replicate's status vocabulary onto the one the frontend already handles
# for Blotato visuals, so a single poll loop works for both providers.
STATUS_MAP = {
    "starting": "queueing",
    "processing": "generating-media",
    "succeeded": "done",
    "failed": "failed",
    "canceled": "failed",
}

# Statuses that mean the credit reserved for this generation must be refunded.
FAILED_STATUSES = {"failed"}
DONE_STATUS = "done"


class ReplicateService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # -- configuration -----------------------------------------------------

    def is_enabled(self) -> bool:
        return self.settings.replicate_is_enabled()

    def _base_url(self) -> str:
        return self.settings.replicate_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        token = self.settings.replicate_key()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _require_enabled(self) -> None:
        if not self.settings.replicate_enabled:
            raise ReplicateServiceError(
                "Replicate не подключён. Генерация ИИ-видео недоступна."
            )
        if not self.settings.replicate_token_configured():
            raise ConfigurationError(
                "Required environment variable REPLICATE_API_TOKEN is missing."
            )

    def _model_for(self, kind: str) -> str:
        model = self.settings.replicate_model(kind)
        if not model:
            raise ReplicateServiceError(
                "Для этого типа медиа не настроена модель Replicate."
            )
        return model

    # -- low-level HTTP ----------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        self._require_enabled()
        try:
            async with httpx.AsyncClient(timeout=REPLICATE_TIMEOUT_SECONDS) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning("Replicate request failed: %s", type(exc).__name__)
            raise ReplicateServiceError(
                "Не удалось связаться с Replicate.",
                provider_message=type(exc).__name__,
            ) from exc
        if response.status_code >= 400:
            provider_message = self._safe_provider_message(response)
            logger.warning("Replicate responded with status %s", response.status_code)
            raise ReplicateServiceError(
                "Не удалось сгенерировать медиа через Replicate.",
                status=response.status_code,
                provider_message=provider_message,
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    @staticmethod
    def _safe_provider_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:300]
        if isinstance(payload, dict):
            for key in ("detail", "message", "error", "title"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:300]
        return str(payload)[:300]

    # -- predictions -------------------------------------------------------

    async def create_prediction(self, *, kind: str, prompt: str) -> dict[str, Any]:
        model = self._model_for(kind)
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise ReplicateServiceError("Опишите, что должно быть на видео.")
        body: dict[str, Any] = {"input": {"prompt": clean_prompt}}
        if ":" in model:
            # owner/name:version -> versioned predictions endpoint.
            version = model.split(":", 1)[1].strip()
            body["version"] = version
            url = f"{self._base_url()}/predictions"
        else:
            # owner/name -> run the model's latest version.
            url = f"{self._base_url()}/models/{model.strip('/')}/predictions"
        payload = await self._request("POST", url, json=body)
        return self._normalize(payload)

    async def get_prediction(self, prediction_id: str) -> dict[str, Any]:
        url = f"{self._base_url()}/predictions/{prediction_id.strip()}"
        payload = await self._request("GET", url)
        return self._normalize(payload)

    @staticmethod
    def _normalize(payload: Any) -> dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        prediction_id = data.get("id")
        raw_status = str(data.get("status") or "starting").strip().lower()
        status = STATUS_MAP.get(raw_status, "generating-media")
        media_urls = ReplicateService._extract_urls(data.get("output"))
        error = data.get("error")
        return {
            "id": str(prediction_id) if prediction_id is not None else None,
            "status": status,
            "media_urls": media_urls,
            "error": str(error) if error else None,
        }

    @staticmethod
    def _extract_urls(output: Any) -> list[str]:
        urls: list[str] = []
        if isinstance(output, str):
            if output.strip():
                urls.append(output.strip())
        elif isinstance(output, list):
            for item in output:
                if isinstance(item, str) and item.strip():
                    urls.append(item.strip())
        elif isinstance(output, dict):
            # Some models return {"video": "https://..."} or similar.
            for value in output.values():
                if isinstance(value, str) and value.strip():
                    urls.append(value.strip())
        return list(dict.fromkeys(urls))
