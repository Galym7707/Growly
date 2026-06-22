"""Blotato social-publishing provider.

The backend is the only component that talks to Blotato. The frontend never
calls Blotato and never receives the API key. Authentication uses the
``blotato-api-key`` request header expected by the Blotato v2 API.

The exact request/response field names of the Blotato API are kept in the
``*_FIELD`` / ``PLATFORM_TARGET`` constants below so they are easy to adjust if
the provider contract changes; parsing is defensive about alternative names.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.database import session_scope
from app.repositories.integrations_repo import IntegrationsRepository
from app.utils.errors import BlotatoServiceError, ConfigurationError

logger = logging.getLogger(__name__)

BLOTATO_API_KEY_HEADER = "blotato-api-key"
BLOTATO_TIMEOUT_SECONDS = 30.0

# Platforms Growly can auto-publish through Blotato. Any platform returned by
# the Blotato accounts endpoint is also accepted, even if not listed here.
SUPPORTED_PLATFORMS = {
    "instagram",
    "threads",
    "tiktok",
    "youtube",
    "facebook",
    "linkedin",
    "x",
    "bluesky",
    "pinterest",
}

# Growly platform slug -> Blotato target type.
PLATFORM_TARGET = {
    "x": "twitter",
}

# Platforms that publish to a page/organization in addition to an account.
PAGE_PLATFORMS = {"facebook", "linkedin"}

VISUAL_TEMPLATE_IDS = {
    "image": "53cfec04-2500-41cf-8cc1-ba670d2c341a",
    "video": "5903fe43-514d-40ee-a060-0d6628c5f8fd",
}

MEDIA_EXTENSIONS = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}


class BlotatoService:
    def __init__(
        self,
        settings: Settings | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        # A workspace-level key (stored by the user in the UI) takes priority
        # over the env-level key; either makes the integration usable.
        self._api_key_override = (api_key or "").strip() or None

    # -- configuration -----------------------------------------------------

    def _effective_key(self) -> str | None:
        # A workspace-level key (set by the user in the UI) always wins. The
        # env-level key is only used when BLOTATO_ENABLED is on, preserving the
        # legacy single-tenant behaviour.
        if self._api_key_override:
            return self._api_key_override
        if self.settings.blotato_enabled and self.settings.blotato_api_key_configured():
            return self.settings.blotato_key()
        return None

    def api_key_configured(self) -> bool:
        return self._effective_key() is not None

    def is_enabled(self) -> bool:
        # Enabled whenever a usable key exists (workspace override or the env
        # key gated by BLOTATO_ENABLED).
        return self.api_key_configured()

    def validate_platform(self, platform: str) -> bool:
        slug = (platform or "").strip().lower()
        return bool(slug) and slug != "telegram"

    @staticmethod
    def target_type(platform: str) -> str:
        slug = (platform or "").strip().lower()
        return PLATFORM_TARGET.get(slug, slug)

    def _base_url(self) -> str:
        return self.settings.blotato_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        key = self._effective_key()
        if not key:
            raise ConfigurationError("Blotato API key is not configured.")
        return {
            BLOTATO_API_KEY_HEADER: key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _require_enabled(self) -> None:
        if not self._api_key_override and not self.settings.blotato_enabled:
            raise BlotatoServiceError(
                "Blotato не подключён. Автопубликация в соцсети временно недоступна."
            )
        if not self.api_key_configured():
            raise ConfigurationError(
                "Required environment variable BLOTATO_API_KEY is missing."
            )

    # -- low-level HTTP ----------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        self._require_enabled()
        url = f"{self._base_url()}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=BLOTATO_TIMEOUT_SECONDS) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning("Blotato request failed: %s", type(exc).__name__)
            raise BlotatoServiceError(
                "Не удалось связаться с Blotato.",
                provider_message=type(exc).__name__,
            ) from exc
        if response.status_code >= 400:
            # Never include the API key; surface only the provider's message.
            provider_message = self._safe_provider_message(response)
            logger.warning(
                "Blotato responded with status %s", response.status_code
            )
            raise BlotatoServiceError(
                "Не удалось отправить публикацию.",
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
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:300]
        return str(payload)[:300]

    # -- accounts ----------------------------------------------------------

    @staticmethod
    def _account_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("accounts", "data", "items", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    @classmethod
    def _normalize_account(cls, row: dict[str, Any]) -> dict[str, Any]:
        account_id = (
            row.get("id")
            or row.get("accountId")
            or row.get("account_id")
            or row.get("uuid")
        )
        platform = (
            row.get("platform")
            or row.get("targetType")
            or row.get("target_type")
            or row.get("type")
            or ""
        )
        username = (
            row.get("username")
            or row.get("handle")
            or row.get("name")
            or row.get("screenName")
            or ""
        )
        display_name = (
            row.get("displayName")
            or row.get("display_name")
            or row.get("title")
            or row.get("name")
            or username
        )
        status = str(row.get("status") or "connected").strip().lower()
        return {
            "id": str(account_id) if account_id is not None else "",
            "platform": str(platform).strip().lower(),
            "name": str(username),
            "display_name": str(display_name),
            "connected": status in {"connected", "active", "ready", ""},
        }

    async def list_accounts(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/users/me/accounts")
        accounts = [
            self._normalize_account(row) for row in self._account_rows(payload)
        ]
        return [account for account in accounts if account["id"]]

    def config_status(self) -> dict[str, Any]:
        """Lightweight config check (no network): is a key present?"""
        return {
            "api_key_configured": self.api_key_configured(),
            "base_url": self._base_url(),
        }

    async def validate_config(self) -> dict[str, Any]:
        """Verify the configured key works by listing accounts."""
        if not self.api_key_configured():
            raise BlotatoServiceError(
                "BLOTATO_API_KEY не настроен на сервере.",
            )
        return await self.validate_api_key()

    async def validate_api_key(self) -> dict[str, Any]:
        """Verify the current key against Blotato by listing accounts.

        Raises ``BlotatoServiceError`` on any provider/transport failure so the
        caller can surface a friendly message without leaking the key.
        """

        accounts = await self.list_accounts()
        return {"ok": True, "accounts_count": len(accounts), "accounts": accounts}

    async def get_account(self, account_id: str) -> dict[str, Any] | None:
        for account in await self.list_accounts():
            if account["id"] == str(account_id):
                return account
        return None

    async def test_connection(self) -> dict[str, Any]:
        accounts = await self.list_accounts()
        return {
            "ok": True,
            "message": "Blotato подключён",
            "accounts_count": len(accounts),
        }

    # -- platform -> account mapping --------------------------------------

    def map_platform_to_account(
        self,
        workspace_id: str | None,
        platform: str,
    ) -> dict[str, str | None] | None:
        """Resolve the account/page to publish to for a platform.

        Priority: saved workspace mapping (publication_targets) → env fallback
        account ids. Returns ``None`` when no account can be resolved.
        """

        slug = (platform or "").strip().lower()

        def load() -> dict[str, str | None] | None:
            with session_scope() as session:
                target = IntegrationsRepository(session).get_target(
                    workspace_id, slug
                )
                if target and target.enabled and target.account_id:
                    return {
                        "account_id": target.account_id,
                        "page_id": target.page_id,
                    }
                return None

        mapped = load()
        if mapped:
            return mapped
        fallback_account = self.settings.blotato_fallback_account(slug)
        if fallback_account:
            return {
                "account_id": fallback_account,
                "page_id": self.settings.blotato_fallback_page(slug),
            }
        return None

    # -- publishing --------------------------------------------------------

    async def publish_post(
        self,
        *,
        platform: str,
        account_id: str,
        text: str,
        media_urls: list[str] | None = None,
        page_id: str | None = None,
        scheduled_time: str | None = None,
    ) -> dict[str, Any]:
        target_type = self.target_type(platform)
        post: dict[str, Any] = {
            "accountId": str(account_id),
            "target": {"targetType": target_type},
            "content": {
                "text": text,
                "mediaUrls": media_urls or [],
                "platform": target_type,
            },
        }
        if page_id and platform.strip().lower() in PAGE_PLATFORMS:
            post["target"]["pageId"] = str(page_id)
        body: dict[str, Any] = {"post": post}
        if scheduled_time:
            body["scheduledTime"] = scheduled_time
        payload = await self._request("POST", "/posts", json=body)
        return self._normalize_submission(payload)

    async def create_media_upload(self, filename: str) -> dict[str, str]:
        safe_name = Path((filename or "").strip()).name
        extension = Path(safe_name).suffix.lower()
        if not safe_name or extension not in MEDIA_EXTENSIONS:
            raise BlotatoServiceError(
                "Поддерживаются изображения JPG, PNG, WEBP, GIF и видео MP4, MOV, WEBM."
            )
        payload = await self._request(
            "POST",
            "/media/uploads",
            json={"filename": safe_name[:240]},
        )
        data = payload if isinstance(payload, dict) else {}
        presigned_url = data.get("presignedUrl") or data.get("presigned_url")
        public_url = data.get("publicUrl") or data.get("public_url")
        if not presigned_url or not public_url:
            raise BlotatoServiceError(
                "Blotato не вернул ссылку для загрузки файла."
            )
        return {
            "presigned_url": str(presigned_url),
            "public_url": str(public_url),
        }

    async def create_visual(
        self,
        *,
        kind: str,
        prompt: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        template_id = VISUAL_TEMPLATE_IDS.get((kind or "").strip().lower())
        if not template_id:
            raise BlotatoServiceError("Неизвестный тип медиа для генерации.")
        body: dict[str, Any] = {
            "templateId": template_id,
            "inputs": {},
            "prompt": prompt.strip(),
            "render": True,
        }
        if title and title.strip():
            body["title"] = title.strip()[:200]
        payload = await self._request(
            "POST", "/videos/from-templates", json=body
        )
        return self._normalize_visual(payload)

    async def get_visual_status(self, visual_id: str) -> dict[str, Any]:
        payload = await self._request(
            "GET", f"/videos/creations/{visual_id.strip()}"
        )
        return self._normalize_visual(payload)

    async def schedule_post(
        self,
        *,
        platform: str,
        account_id: str,
        text: str,
        scheduled_time: str,
        media_urls: list[str] | None = None,
        page_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.publish_post(
            platform=platform,
            account_id=account_id,
            text=text,
            media_urls=media_urls,
            page_id=page_id,
            scheduled_time=scheduled_time,
        )

    async def get_post_status(self, post_submission_id: str) -> dict[str, Any]:
        payload = await self._request("GET", f"/posts/{post_submission_id}")
        return self._normalize_submission(payload)

    @staticmethod
    def _normalize_submission(payload: Any) -> dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        submission_id = (
            data.get("submissionId")
            or data.get("postSubmissionId")
            or data.get("id")
            or data.get("post_submission_id")
        )
        url = (
            data.get("url")
            or data.get("postUrl")
            or data.get("post_url")
            or data.get("permalink")
        )
        status = str(data.get("status") or "submitted").strip().lower()
        return {
            "post_submission_id": (
                str(submission_id) if submission_id is not None else None
            ),
            "status": status,
            "url": str(url) if url else None,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _normalize_visual(payload: Any) -> dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        item = data.get("item") if isinstance(data.get("item"), dict) else data
        visual_id = item.get("id") or item.get("creationId")
        media_url = item.get("mediaUrl") or item.get("media_url")
        image_urls = item.get("imageUrls") or item.get("image_urls") or []
        urls = [str(url) for url in image_urls if isinstance(url, str) and url]
        if isinstance(media_url, str) and media_url:
            urls.append(media_url)
        return {
            "id": str(visual_id) if visual_id is not None else None,
            "status": str(item.get("status") or "queueing").strip().lower(),
            "media_urls": list(dict.fromkeys(urls)),
        }
