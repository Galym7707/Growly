"""Orchestrates social publishing across Telegram (Bot API), Blotato (Instagram,
Threads, TikTok, YouTube, Facebook, LinkedIn, X, …) and manual packages.

The backend is the single source of business logic. Publishing records are
persisted in Supabase so n8n and the UI can read status. No secrets are ever
returned to the frontend.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from sqlalchemy import desc, select

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import Draft, ManualPublishPackage, Publication, SocialAccount
from app.repositories.integrations_repo import IntegrationsRepository
from app.services.blotato_service import BlotatoService
from app.utils.crypto import decrypt_secret, encrypt_secret
from app.utils.errors import BlotatoServiceError, GrowlyError

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE = "default"

# Platforms surfaced in the publishing UI. Telegram uses the Bot API; the rest
# use Blotato when connected.
PUBLISHABLE_PLATFORMS = [
    "telegram",
    "instagram",
    "threads",
    "tiktok",
    "youtube",
    "facebook",
    "linkedin",
    "x",
    "bluesky",
    "pinterest",
]

VIDEO_PLATFORMS = {"tiktok", "youtube"}
_ACCOUNT_SYNC_LOCK = Lock()


def normalize_workspace(workspace_id: str | None) -> str:
    value = (workspace_id or "").strip()
    return value or DEFAULT_WORKSPACE


class SocialPublishingService:
    def __init__(
        self,
        settings: Settings | None = None,
        blotato: BlotatoService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._injected_blotato = blotato
        self.blotato = blotato or BlotatoService(self.settings)

    # -- per-workspace Blotato client --------------------------------------

    @staticmethod
    def _stored_api_key(workspace: str) -> str | None:
        try:
            with session_scope() as session:
                ref = IntegrationsRepository(session).get_api_key_ref(
                    workspace, "blotato"
                )
        except Exception:  # noqa: BLE001 - missing DB must not block env fallback
            logger.warning("Could not load stored Blotato key; using env fallback.")
            return None
        return decrypt_secret(ref) if ref else None

    async def _blotato(self, workspace_id: str | None) -> BlotatoService:
        """Resolve the Blotato client for a workspace.

        Priority: an injected client (tests) → a workspace key stored via the UI
        → the shared env-configured client. Returning ``self.blotato`` when there
        is no stored key keeps the env path (and test monkeypatching) intact.
        """

        if self._injected_blotato is not None:
            return self._injected_blotato
        workspace = normalize_workspace(workspace_id)
        stored_key = await asyncio.to_thread(self._stored_api_key, workspace)
        if stored_key:
            return BlotatoService(self.settings, api_key=stored_key)
        return self.blotato

    # -- status ------------------------------------------------------------

    def _telegram_connected(self) -> bool:
        token = self.settings.telegram_bot_api_key
        return bool(token and token.get_secret_value().strip())

    def _notion_connected(self) -> bool:
        key = self.settings.notion_api_key
        return bool(key and key.get_secret_value().strip())

    async def integrations_status(self, workspace_id: str | None) -> dict[str, Any]:
        blotato = await self.blotato_status(workspace_id)
        return {
            "telegram": {
                "connected": self._telegram_connected(),
                "channel_id": self.settings.telegram_publish_target(),
            },
            "notion": {
                "connected": self._notion_connected(),
                "root_configured": bool(
                    (self.settings.notion_root_page_id or "").strip()
                ),
            },
            "blotato": {
                "enabled": blotato["enabled"],
                "connected": blotato["connected"],
                "accounts_count": blotato["accounts_count"],
                "instagram": blotato.get("instagram"),
            },
        }

    async def blotato_status(self, workspace_id: str | None) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        integration, rows, targets = await asyncio.to_thread(
            self._load_blotato_state, workspace
        )
        configured = bool(integration and integration.api_key_encrypted)
        configured = configured or self.blotato.api_key_configured()
        # "enabled" mirrors whether a usable key exists (UI- or env-supplied).
        enabled = configured
        accounts = [self._account_to_dict(row) for row in rows]
        target_by_platform = {
            target.platform: target for target in targets if target.platform
        }
        metadata = (integration.metadata_json or {}) if integration else {}
        stored_count = int(metadata.get("accounts_count") or 0)
        accounts_count = len(accounts) or stored_count
        connected = bool(
            configured
            and integration is not None
            and (integration.status == "connected" or accounts_count > 0)
        )
        last_checked_at = (
            integration.last_checked_at.isoformat()
            if integration and integration.last_checked_at
            else None
        )
        instagram = self._platform_status("instagram", accounts, target_by_platform)
        platform_statuses = {
            platform: self._platform_status(platform, accounts, target_by_platform)
            for platform in PUBLISHABLE_PLATFORMS
            if platform != "telegram"
        }
        return {
            "enabled": enabled,
            "api_key_configured": configured,
            "connected": connected,
            "accounts_count": accounts_count,
            "last_checked_at": last_checked_at,
            "instagram": instagram,
            "platforms": platform_statuses,
        }

    @staticmethod
    def _load_blotato_state(
        workspace: str,
    ) -> tuple[Any | None, list[SocialAccount], list[Any]]:
        try:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                integration = repo.get_integration(workspace, "blotato")
                accounts = repo.list_accounts(workspace, "blotato")
                targets = repo.list_targets(workspace)
                return integration, accounts, targets
        except Exception:  # noqa: BLE001 - read-only status should degrade safely
            logger.warning("Could not load cached Blotato state.")
            return None, [], []

    @staticmethod
    def _platform_status(
        platform: str,
        accounts: list[dict[str, Any]],
        targets: dict[str, Any],
    ) -> dict[str, Any]:
        target = targets.get(platform)
        account_id = target.account_id if target else None
        account = None
        if account_id:
            account = next(
                (a for a in accounts if str(a.get("id")) == str(account_id)), None
            )
        return {
            "selected": bool(account_id),
            "account_id": account_id,
            "account_name": (
                (account.get("display_name") or account.get("name"))
                if account
                else None
            ),
            "available_count": sum(
                1 for a in accounts if a.get("platform") == platform
            ),
        }

    @staticmethod
    def _record_integration_status(
        workspace: str,
        enabled: bool,
        connected: bool,
        accounts_count: int,
    ) -> None:
        with session_scope() as session:
            IntegrationsRepository(session).upsert_integration(
                workspace_id=workspace,
                provider="blotato",
                enabled=enabled,
                status="connected" if connected else "disconnected",
                metadata={"accounts_count": accounts_count},
                last_checked_at=datetime.now(UTC),
            )

    @staticmethod
    def _stored_accounts_count(workspace: str) -> int:
        with session_scope() as session:
            return len(
                IntegrationsRepository(session).list_accounts(workspace, "blotato")
            )

    # -- accounts ----------------------------------------------------------

    async def refresh_accounts(self, workspace_id: str | None) -> list[dict[str, Any]]:
        blotato = await self._blotato(workspace_id)
        if not blotato.is_enabled():
            raise BlotatoServiceError(
                "Blotato не подключён. Автопубликация в соцсети временно недоступна."
            )
        workspace = normalize_workspace(workspace_id)
        accounts = await blotato.list_accounts()
        await asyncio.to_thread(self._store_accounts, workspace, accounts)
        return accounts

    @staticmethod
    def _store_accounts(workspace: str, accounts: list[dict[str, Any]]) -> None:
        with _ACCOUNT_SYNC_LOCK:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                repo.replace_accounts(
                    workspace_id=workspace,
                    provider="blotato",
                    accounts=accounts,
                )
                repo.upsert_integration(
                    workspace_id=workspace,
                    provider="blotato",
                    enabled=True,
                    status="connected",
                    metadata={"accounts_count": len(accounts)},
                    last_checked_at=datetime.now(UTC),
                )
                SocialPublishingService._ensure_default_mappings(
                    repo, workspace, accounts
                )

    async def create_media_upload(
        self, workspace_id: str | None, filename: str
    ) -> dict[str, str]:
        blotato = await self._blotato(workspace_id)
        return await blotato.create_media_upload(filename)

    async def create_visual(
        self,
        workspace_id: str | None,
        *,
        kind: str,
        prompt: str,
        title: str | None,
    ) -> dict[str, Any]:
        blotato = await self._blotato(workspace_id)
        return await blotato.create_visual(kind=kind, prompt=prompt, title=title)

    async def visual_status(
        self, workspace_id: str | None, visual_id: str
    ) -> dict[str, Any]:
        blotato = await self._blotato(workspace_id)
        return await blotato.get_visual_status(visual_id)

    async def list_accounts(self, workspace_id: str | None) -> list[dict[str, Any]]:
        workspace = normalize_workspace(workspace_id)
        rows = await asyncio.to_thread(self._load_accounts, workspace)
        return [self._account_to_dict(row) for row in rows]

    @staticmethod
    def _load_accounts(workspace: str) -> list[SocialAccount]:
        try:
            with session_scope() as session:
                return IntegrationsRepository(session).list_accounts(
                    workspace, "blotato"
                )
        except Exception:  # noqa: BLE001 - read-only accounts should degrade safely
            logger.warning("Could not load cached Blotato accounts.")
            return []

    @staticmethod
    def _account_to_dict(row: SocialAccount) -> dict[str, Any]:
        return {
            "id": row.external_account_id or "",
            "platform": row.platform or "",
            "name": row.username or "",
            "display_name": row.display_name or row.username or "",
            "connected": row.status == "connected",
            "subaccounts": (row.metadata_json or {}).get("subaccounts") or [],
        }

    async def test_connection(self, workspace_id: str | None) -> dict[str, Any]:
        blotato = await self._blotato(workspace_id)
        if not blotato.is_enabled():
            raise BlotatoServiceError(
                "Blotato не подключён. Автопубликация в соцсети временно недоступна."
            )
        result = await blotato.test_connection()
        await asyncio.to_thread(
            self._record_integration_status,
            normalize_workspace(workspace_id),
            True,
            True,
            int(result.get("accounts_count") or 0),
        )
        return result

    # -- connect / disconnect ---------------------------------------------

    async def save_api_key(
        self, workspace_id: str | None, api_key: str
    ) -> dict[str, Any]:
        """Validate the key against Blotato, then store it encrypted (backend
        only). The key is never returned to the caller."""

        cleaned = (api_key or "").strip()
        if not cleaned:
            raise GrowlyError("Введите API-ключ Blotato.")
        probe = BlotatoService(self.settings, api_key=cleaned)
        result = await probe.validate_api_key()
        accounts = result.get("accounts") or []
        workspace = normalize_workspace(workspace_id)
        encrypted = encrypt_secret(cleaned)
        await asyncio.to_thread(
            self._persist_api_key, workspace, encrypted, accounts
        )
        return {
            "ok": True,
            "connected": True,
            "accounts_count": len(accounts),
        }

    @staticmethod
    def _persist_api_key(
        workspace: str,
        encrypted: str,
        accounts: list[dict[str, Any]],
    ) -> None:
        with session_scope() as session:
            repo = IntegrationsRepository(session)
            repo.set_api_key(
                workspace_id=workspace,
                provider="blotato",
                api_key_encrypted=encrypted,
                status="connected",
                enabled=True,
            )
            repo.upsert_integration(
                workspace_id=workspace,
                provider="blotato",
                enabled=True,
                status="connected",
                metadata={"accounts_count": len(accounts)},
                last_checked_at=datetime.now(UTC),
            )
            repo.replace_accounts(
                workspace_id=workspace, provider="blotato", accounts=accounts
            )
            SocialPublishingService._ensure_default_mappings(repo, workspace, accounts)

    @staticmethod
    def _ensure_default_mappings(
        repo: IntegrationsRepository,
        workspace: str,
        accounts: list[dict[str, Any]],
    ) -> None:
        """Select the first connected account per platform when no valid
        mapping exists yet. Users can override the selection in the UI.
        """

        first_by_platform: dict[str, dict[str, Any]] = {}
        valid_ids: set[str] = set()
        for account in accounts:
            account_id = str(account.get("id") or "").strip()
            platform = str(account.get("platform") or "").strip().lower()
            if not account_id or not platform or not account.get("connected", True):
                continue
            valid_ids.add(account_id)
            first_by_platform.setdefault(platform, account)

        targets = {target.platform: target for target in repo.list_targets(workspace)}
        for platform, account in first_by_platform.items():
            target = targets.get(platform)
            if target and target.enabled and target.account_id in valid_ids:
                continue
            repo.set_mapping(
                workspace_id=workspace,
                platform=platform,
                account_id=str(account.get("id")),
                page_id=SocialPublishingService._default_page_id(platform, account),
                enabled=True,
            )

    @staticmethod
    def _default_page_id(platform: str, account: dict[str, Any]) -> str | None:
        subaccounts = account.get("subaccounts") or []
        if platform in {"facebook", "linkedin"} and len(subaccounts) == 1:
            value = subaccounts[0].get("id") if isinstance(subaccounts[0], dict) else None
            return str(value) if value else None
        return None

    async def disconnect(self, workspace_id: str | None) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        await asyncio.to_thread(self._clear_integration, workspace)
        return {"ok": True, "connected": False}

    @staticmethod
    def _clear_integration(workspace: str) -> None:
        with session_scope() as session:
            repo = IntegrationsRepository(session)
            repo.set_api_key(
                workspace_id=workspace,
                provider="blotato",
                api_key_encrypted=None,
                status="disconnected",
                enabled=False,
            )
            repo.replace_accounts(
                workspace_id=workspace, provider="blotato", accounts=[]
            )
            repo.clear_mappings(workspace, "blotato")

    async def select_account(
        self, workspace_id: str | None, platform: str, account_id: str | None
    ) -> dict[str, Any]:
        """Save (or clear) the chosen account for a platform (e.g. Instagram)."""

        workspace = normalize_workspace(workspace_id)
        saved = await self.save_mappings(
            workspace, [{"platform": platform, "account_id": account_id}]
        )
        return {"ok": True, "mappings": saved}

    # -- mappings ----------------------------------------------------------

    async def save_mappings(
        self,
        workspace_id: str | None,
        mappings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        workspace = normalize_workspace(workspace_id)

        def save() -> list[dict[str, Any]]:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                account_rows = repo.list_accounts(workspace, "blotato")
                accounts_by_id = {
                    row.external_account_id: row
                    for row in account_rows
                    if row.external_account_id and row.status == "connected"
                }
                for mapping in mappings:
                    platform = str(mapping.get("platform") or "").strip().lower()
                    if not platform:
                        continue
                    account_id = (
                        str(mapping.get("account_id")).strip()
                        if mapping.get("account_id")
                        else None
                    )
                    if account_id:
                        account = accounts_by_id.get(account_id)
                        if account is None or account.platform != platform:
                            raise GrowlyError(
                                "Выберите аккаунт из списка подключённых аккаунтов Blotato."
                            )
                    repo.set_mapping(
                        workspace_id=workspace,
                        platform=platform,
                        account_id=account_id,
                        page_id=(
                            str(mapping.get("page_id"))
                            if mapping.get("page_id")
                            else None
                        ),
                    )
                return [self._target_to_dict(row) for row in repo.list_targets(workspace)]

        return await asyncio.to_thread(save)

    async def get_mappings(self, workspace_id: str | None) -> list[dict[str, Any]]:
        workspace = normalize_workspace(workspace_id)

        def load() -> list[dict[str, Any]]:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                return [self._target_to_dict(row) for row in repo.list_targets(workspace)]

        try:
            return await asyncio.to_thread(load)
        except Exception:  # noqa: BLE001 - read-only mappings should degrade safely
            logger.warning("Could not load Blotato mappings.")
            return []

    @staticmethod
    def _target_to_dict(row: Any) -> dict[str, Any]:
        return {
            "platform": row.platform,
            "account_id": row.account_id,
            "page_id": row.page_id,
            "enabled": row.enabled,
        }

    # -- publishing --------------------------------------------------------

    async def publish_draft(
        self,
        *,
        workspace_id: str | None,
        draft_id: int,
        platforms: list[str],
        publish_now: bool,
        scheduled_time: str | None,
        media_urls: list[str] | None,
        language: str,
    ) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        draft = await asyncio.to_thread(self._load_draft, draft_id)
        if draft is None:
            raise ValueError("Черновик не найден.")
        if not self._draft_visible_in_workspace(draft, workspace):
            raise ValueError("Черновик не найден.")
        text = (draft.draft_text or "").strip()
        if not text:
            raise GrowlyError("Черновик пуст; публикация невозможна.")
        blotato = await self._blotato(workspace_id)
        if not blotato.is_enabled():
            raise BlotatoServiceError(
                "Blotato не подключён. Автопубликация в соцсети временно недоступна."
            )

        submissions: list[dict[str, Any]] = []
        publication_ids: list[int] = []
        for platform in platforms:
            slug = (platform or "").strip().lower()
            if slug == "telegram":
                # Telegram is published via the Bot API, not Blotato.
                submissions.append(
                    {
                        "platform": "telegram",
                        "post_submission_id": None,
                        "status": "skipped",
                        "error": "Telegram публикуется через Telegram, не через Blotato.",
                    }
                )
                continue
            if not blotato.validate_platform(slug):
                submissions.append(
                    {
                        "platform": slug,
                        "post_submission_id": None,
                        "status": "unsupported",
                        "error": "Эта платформа пока не поддерживается для автопубликации.",
                    }
                )
                continue
            existing = await asyncio.to_thread(
                self._load_existing_submission, workspace, draft_id, slug
            )
            if existing is not None:
                publication_ids.append(int(existing["publication_id"]))
                submissions.append(
                    {
                        "platform": slug,
                        "post_submission_id": existing["post_submission_id"],
                        "status": existing["status"],
                        "url": existing["url"],
                    }
                )
                continue
            # Security: the account id is taken ONLY from this workspace's
            # connected social_accounts — never from the request or env.
            mapping = await asyncio.to_thread(
                self._resolve_account, workspace, slug
            )
            if not mapping or not mapping.get("account_id"):
                pub_id = await asyncio.to_thread(
                    self._record_publication,
                    workspace,
                    draft_id,
                    slug,
                    None,
                    None,
                    "failed",
                    None,
                    None,
                    None,
                    "Аккаунт не подключён. Отправьте заявку на подключение в Интеграциях.",
                )
                publication_ids.append(pub_id)
                submissions.append(
                    {
                        "platform": slug,
                        "post_submission_id": None,
                        "status": "failed",
                        "error": "Аккаунт не подключён. Отправьте заявку на подключение в Интеграциях.",
                    }
                )
                continue
            try:
                result = await blotato.publish_post(
                    platform=slug,
                    account_id=str(mapping["account_id"]),
                    text=text,
                    media_urls=media_urls,
                    page_id=mapping.get("page_id"),
                    scheduled_time=None if publish_now else scheduled_time,
                    title=getattr(draft, "title", None),
                )
                status = "scheduled" if not publish_now and scheduled_time else "submitted"
                pub_id = await asyncio.to_thread(
                    self._record_publication,
                    workspace,
                    draft_id,
                    slug,
                    str(mapping["account_id"]),
                    mapping.get("page_id"),
                    status,
                    None if publish_now else scheduled_time,
                    result.get("post_submission_id"),
                    result.get("url"),
                    None,
                )
                publication_ids.append(pub_id)
                submissions.append(
                    {
                        "platform": slug,
                        "post_submission_id": result.get("post_submission_id"),
                        "status": status,
                        "url": result.get("url"),
                    }
                )
            except BlotatoServiceError as exc:
                provider_message = (exc.provider_message or "").strip()
                error_message = str(exc)
                if provider_message and provider_message != error_message:
                    error_message = f"{error_message} Blotato: {provider_message}"
                pub_id = await asyncio.to_thread(
                    self._record_publication,
                    workspace,
                    draft_id,
                    slug,
                    str(mapping["account_id"]),
                    mapping.get("page_id"),
                    "failed",
                    None,
                    None,
                    None,
                    error_message,
                )
                publication_ids.append(pub_id)
                submissions.append(
                    {
                        "platform": slug,
                        "post_submission_id": None,
                        "status": "failed",
                        "error": error_message,
                    }
                )
        if (
            any(item.get("status") == "submitted" for item in submissions)
            and draft.status != "published"
        ):
            await asyncio.to_thread(self._mark_draft_published, draft_id)
        return {
            "status": "submitted" if publication_ids else "no_targets",
            "publication_ids": publication_ids,
            "blotato_submissions": submissions,
        }

    @staticmethod
    def _load_existing_submission(
        workspace: str,
        draft_id: int,
        platform: str,
    ) -> dict[str, Any] | None:
        """Return an already-submitted publication for retry/idempotency.

        A provider can accept the post while the browser still receives a
        transient 500/network error. Retrying must not create a duplicate post
        for the same draft/platform.
        """

        with session_scope() as session:
            publication = session.scalar(
                select(Publication)
                .where(
                    Publication.workspace_id == workspace,
                    Publication.draft_id == draft_id,
                    Publication.platform == platform,
                    Publication.provider == "blotato",
                    Publication.external_submission_id.is_not(None),
                    Publication.status.in_(("submitted", "scheduled", "published")),
                )
                .order_by(desc(Publication.created_at), desc(Publication.id))
                .limit(1)
            )
            if publication is None:
                return None
            return {
                "publication_id": publication.id,
                "post_submission_id": publication.external_submission_id,
                "status": publication.status,
                "url": publication.external_post_url or publication.published_url,
            }

    @staticmethod
    def _resolve_account(workspace: str, platform: str) -> dict[str, str | None] | None:
        """Resolve the publish account from the workspace's saved user mapping.

        The frontend writes ``publication_targets`` when the user selects an
        account in settings. Admin-linked ``social_accounts`` remain a legacy
        fallback for older workspaces.
        """
        with session_scope() as session:
            repo = IntegrationsRepository(session)
            target = repo.get_target(workspace, platform)
            if target and target.enabled and target.account_id:
                return {
                    "account_id": target.account_id,
                    "page_id": target.page_id,
                }
            account = repo.connected_account(workspace, platform)
            if account and account.external_account_id:
                return {
                    "account_id": account.external_account_id,
                    "page_id": None,
                }
            return None

    @staticmethod
    def _load_draft(draft_id: int) -> Draft | None:
        with session_scope() as session:
            return session.get(Draft, draft_id)

    @staticmethod
    def _draft_visible_in_workspace(draft: Draft, workspace: str) -> bool:
        draft_workspace = getattr(draft, "workspace_id", None)
        if draft_workspace is None:
            return workspace == DEFAULT_WORKSPACE
        return draft_workspace == workspace

    @staticmethod
    def _mark_draft_published(draft_id: int) -> None:
        with session_scope() as session:
            draft = session.get(Draft, draft_id)
            if draft and draft.status != "published":
                draft.status = "published"

    @staticmethod
    def _record_publication(
        workspace: str,
        draft_id: int,
        platform: str,
        account_id: str | None,
        page_id: str | None,
        status: str,
        scheduled_time: str | None,
        submission_id: str | None,
        external_post_url: str | None,
        error_message: str | None,
    ) -> int:
        scheduled = None
        if scheduled_time:
            try:
                scheduled = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            except ValueError:
                scheduled = None
        with session_scope() as session:
            publication = IntegrationsRepository(session).create_publication(
                workspace_id=workspace,
                draft_id=draft_id,
                channel=platform,
                platform=platform,
                provider="blotato",
                account_id=account_id,
                page_id=page_id,
                status=status,
                scheduled_for=scheduled,
                scheduled_time=scheduled,
                external_submission_id=submission_id,
                external_post_url=external_post_url,
                published_at=(datetime.now(UTC) if status == "submitted" else None),
                error_message=error_message,
                metadata_json={},
                metrics_json={},
            )
            return publication.id

    async def publication_status(self, publication_id: int) -> dict[str, Any]:
        publication = await asyncio.to_thread(self._load_publication, publication_id)
        if publication is None:
            raise ValueError("Публикация не найдена.")
        payload = {
            "id": publication.id,
            "platform": publication.platform or publication.channel,
            "provider": publication.provider,
            "status": publication.status,
            "external_submission_id": publication.external_submission_id,
            "external_post_url": publication.external_post_url
            or publication.published_url,
            "error_message": publication.error_message,
            "scheduled_time": (
                publication.scheduled_time.isoformat()
                if publication.scheduled_time
                else None
            ),
            "published_at": (
                publication.published_at.isoformat()
                if publication.published_at
                else None
            ),
        }
        blotato = await self._blotato(publication.workspace_id)
        if (
            publication.provider == "blotato"
            and publication.external_submission_id
            and blotato.is_enabled()
        ):
            try:
                provider_status = await blotato.get_post_status(
                    publication.external_submission_id
                )
                payload["provider_status"] = provider_status.get("status")
                if provider_status.get("url"):
                    payload["external_post_url"] = provider_status["url"]
            except BlotatoServiceError:
                pass
        return payload

    @staticmethod
    def _load_publication(publication_id: int) -> Publication | None:
        with session_scope() as session:
            return session.get(Publication, publication_id)

    # -- manual packages ---------------------------------------------------

    async def create_manual_package(
        self,
        *,
        workspace_id: str | None,
        draft_id: int,
        platforms: list[str],
        language: str,
    ) -> list[dict[str, Any]]:
        workspace = normalize_workspace(workspace_id)
        draft = await asyncio.to_thread(self._load_draft, draft_id)
        if draft is None:
            raise ValueError("Черновик не найден.")
        if not self._draft_visible_in_workspace(draft, workspace):
            raise ValueError("Черновик не найден.")
        text = (draft.draft_text or "").strip()
        if not text:
            raise GrowlyError("Черновик пуст; пакет подготовить нельзя.")
        builder = ManualPackageBuilder(language)
        packages = [
            builder.build(platform, draft.title, text) for platform in platforms
        ]

        def persist() -> list[dict[str, Any]]:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                saved: list[dict[str, Any]] = []
                for package in packages:
                    row = repo.upsert_manual_package(
                        workspace_id=workspace,
                        draft_id=draft_id,
                        platform=package["platform"],
                        caption=package["caption"],
                        hook=package["hook"],
                        script=package["script"],
                        visual_brief=package["visual_brief"],
                        hashtags=package["hashtags"],
                        cta=package["cta"],
                    )
                    saved.append(self._package_to_dict(row))
                return saved

        return await asyncio.to_thread(persist)

    @staticmethod
    def _package_to_dict(row: ManualPublishPackage) -> dict[str, Any]:
        return {
            "id": row.id,
            "platform": row.platform,
            "caption": row.caption,
            "hook": row.hook,
            "script": row.script,
            "visual_brief": row.visual_brief,
            "hashtags": row.hashtags,
            "cta": row.cta,
            "status": row.status,
        }


_MANUAL_COPY = {
    "ru": {
        "cta": "Узнайте больше — напишите нам.",
        "visual": "Чистый кадр по теме поста, фирменные цвета бренда.",
        "video_visual": "Динамичные короткие сцены, крупный план продукта, субтитры.",
        "scene": "Сцена",
        "thread": "Продолжение в комментариях/ответах.",
        "b2b": "Деловой тон, конкретная польза для бизнеса.",
    },
    "en": {
        "cta": "Learn more — message us.",
        "visual": "Clean on-topic shot using the brand colors.",
        "video_visual": "Dynamic short scenes, product close-up, captions.",
        "scene": "Scene",
        "thread": "Continue in replies.",
        "b2b": "Professional tone, concrete business value.",
    },
    "kk": {
        "cta": "Толығырақ — бізге жазыңыз.",
        "visual": "Тақырыпқа сай таза кадр, бренд түстері.",
        "video_visual": "Динамикалық қысқа сахналар, өнімнің ірі планы, субтитрлер.",
        "scene": "Сахна",
        "thread": "Жалғасы — жауаптарда.",
        "b2b": "Іскерлік үн, бизнеске нақты пайда.",
    },
}


class ManualPackageBuilder:
    """Deterministic, language-aware content adaptation per platform.

    Always produces a usable package so the manual fallback works even when
    Blotato (or the AI provider) is unavailable.
    """

    def __init__(self, language: str) -> None:
        self.language = language if language in _MANUAL_COPY else "ru"
        self.copy = _MANUAL_COPY[self.language]

    @staticmethod
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return text.strip()[:120]

    @staticmethod
    def _hashtags(title: str | None, text: str) -> str:
        words = [
            word.strip("#.,!?:;()[]\"'«»").lower()
            for word in f"{title or ''} {text}".split()
        ]
        seen: list[str] = []
        for word in words:
            if len(word) >= 5 and word.isalpha() and word not in seen:
                seen.append(word)
            if len(seen) >= 5:
                break
        return " ".join(f"#{word}" for word in seen)

    def build(self, platform: str, title: str | None, text: str) -> dict[str, Any]:
        slug = (platform or "").strip().lower()
        hook = self._first_line(text)
        cta = self.copy["cta"]
        hashtags = self._hashtags(title, text)
        script = ""
        visual = self.copy["visual"]
        caption = text

        if slug in VIDEO_PLATFORMS:
            visual = self.copy["video_visual"]
            scenes = [
                f"{self.copy['scene']} 1 (0-5с): {hook}",
                f"{self.copy['scene']} 2 (5-20с): {text[:200]}",
                f"{self.copy['scene']} 3 (20-30с): {cta}",
            ]
            script = "\n".join(scenes)
        elif slug == "threads":
            chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
            script = "\n\n---\n\n".join(chunks[:5]) or text
        elif slug == "linkedin":
            caption = f"{text}\n\n{self.copy['b2b']}"
        elif slug == "x":
            caption = text[:270]

        return {
            "platform": slug,
            "caption": caption.strip(),
            "hook": hook,
            "script": script,
            "visual_brief": visual,
            "hashtags": hashtags,
            "cta": cta,
        }
