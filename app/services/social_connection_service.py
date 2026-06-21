"""Admin-assisted social account connection (manual MVP).

Regular users submit a request to connect a social account (e.g. Instagram).
The Growly owner completes the official OAuth connection inside Blotato manually
(on a call with the client) and then links the resulting Blotato account id to
the user's workspace via the admin panel. No passwords are ever requested or
stored, and the BLOTATO_API_KEY lives only in backend env.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import SocialAccount, SocialConnectionRequest
from app.repositories.integrations_repo import IntegrationsRepository
from app.services.blotato_service import BlotatoService
from app.services.social_publishing_service import normalize_workspace
from app.utils.errors import BlotatoServiceError, GrowlyError

logger = logging.getLogger(__name__)

ACTIVE_REQUEST_STATES = {"pending", "in_progress"}
VALID_REQUEST_STATES = {
    "pending",
    "in_progress",
    "connected",
    "cancelled",
    "failed",
}


class SocialConnectionService:
    def __init__(
        self,
        settings: Settings | None = None,
        blotato: BlotatoService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.blotato = blotato or BlotatoService(self.settings)

    # -- serialization -----------------------------------------------------

    @staticmethod
    def _account_payload(account: SocialAccount | None) -> dict[str, Any] | None:
        if account is None:
            return None
        return {
            "platform": account.platform,
            "provider": account.provider,
            "external_account_id": account.external_account_id,
            "username": account.username,
            "display_name": account.display_name or account.username,
            "status": account.status,
            "connected_at": (
                account.connected_at.isoformat() if account.connected_at else None
            ),
            "last_checked_at": (
                account.last_checked_at.isoformat()
                if account.last_checked_at
                else None
            ),
        }

    @staticmethod
    def _request_payload(
        request: SocialConnectionRequest | None,
    ) -> dict[str, Any] | None:
        if request is None:
            return None
        return {
            "id": request.id,
            "workspace_id": request.workspace_id,
            "user_email": request.user_email,
            "platform": request.platform,
            "requested_username": request.requested_username,
            "status": request.status,
            "admin_note": request.admin_note,
            "user_note": request.user_note,
            "created_at": (
                request.created_at.isoformat() if request.created_at else None
            ),
            "resolved_at": (
                request.resolved_at.isoformat() if request.resolved_at else None
            ),
        }

    # -- user-facing -------------------------------------------------------

    async def status(
        self, workspace_id: str | None, platform: str = "instagram"
    ) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        return await asyncio.to_thread(self._status_sync, workspace, platform)

    def _status_sync(self, workspace: str, platform: str) -> dict[str, Any]:
        with session_scope() as session:
            repo = IntegrationsRepository(session)
            account = repo.connected_account(workspace, platform)
            request = repo.latest_request(workspace, platform)
            account_payload = self._account_payload(account)
            request_payload = self._request_payload(request)

        if account_payload:
            state = "connected"
        elif request and request.status == "failed":
            state = "failed"
        elif request and request.status in ACTIVE_REQUEST_STATES:
            state = request.status  # pending | in_progress
        else:
            state = "not_connected"

        return {
            "platform": platform,
            "state": state,
            "account": account_payload,
            "request": request_payload,
        }

    async def create_request(
        self,
        workspace_id: str | None,
        user_email: str | None,
        platform: str,
        username: str | None,
    ) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        slug = (platform or "instagram").strip().lower()

        def run() -> None:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                if repo.connected_account(workspace, slug):
                    raise GrowlyError("Этот аккаунт уже подключён.")
                existing = repo.latest_request(workspace, slug)
                if existing and existing.status in ACTIVE_REQUEST_STATES:
                    return  # idempotent: an active request already exists
                repo.create_request(
                    workspace_id=workspace,
                    user_email=user_email,
                    platform=slug,
                    requested_username=(username or "").strip() or None,
                )

        await asyncio.to_thread(run)
        return await self.status(workspace, slug)

    async def cancel_request(
        self, workspace_id: str | None, request_id: int
    ) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)

        def run() -> str:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                request = repo.get_request(request_id)
                if request is None or request.workspace_id != workspace:
                    raise GrowlyError("Заявка не найдена.")
                if request.status == "connected":
                    raise GrowlyError(
                        "Аккаунт уже подключён; заявку отменить нельзя."
                    )
                repo.update_request_status(request_id, "cancelled")
                return request.platform

        platform = await asyncio.to_thread(run)
        return await self.status(workspace, platform)

    async def disconnect(
        self, workspace_id: str | None, platform: str = "instagram"
    ) -> dict[str, Any]:
        workspace = normalize_workspace(workspace_id)
        slug = (platform or "instagram").strip().lower()

        def run() -> None:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                repo.unlink_account(workspace, slug)
                request = repo.latest_request(workspace, slug)
                if request and request.status in {
                    *ACTIVE_REQUEST_STATES,
                    "connected",
                }:
                    repo.update_request_status(request.id, "cancelled")

        await asyncio.to_thread(run)
        return await self.status(workspace, slug)

    # -- admin -------------------------------------------------------------

    async def admin_blotato_status(self) -> dict[str, Any]:
        status = self.blotato.config_status()
        connected = False
        accounts_count = 0
        if self.blotato.api_key_configured():
            try:
                result = await self.blotato.validate_config()
                connected = True
                accounts_count = int(result.get("accounts_count") or 0)
            except BlotatoServiceError:
                connected = False
        return {
            "api_key_configured": status["api_key_configured"],
            "base_url": status["base_url"],
            "connected": connected,
            "accounts_count": accounts_count,
            "last_checked_at": datetime.now(UTC).isoformat(),
        }

    async def admin_list_accounts(self) -> list[dict[str, Any]]:
        accounts = await self.blotato.list_accounts()
        linked = await asyncio.to_thread(self._linked_index)
        for account in accounts:
            link = linked.get(str(account.get("id")))
            account["linked_workspace_id"] = link.get("workspace_id") if link else None
            account["linked_status"] = link.get("status") if link else None
        return accounts

    @staticmethod
    def _linked_index() -> dict[str, dict[str, Any]]:
        with session_scope() as session:
            from sqlalchemy import select

            rows = session.scalars(
                select(SocialAccount).where(SocialAccount.provider == "blotato")
            )
            index: dict[str, dict[str, Any]] = {}
            for row in rows:
                if row.external_account_id:
                    index[row.external_account_id] = {
                        "workspace_id": row.workspace_id,
                        "status": row.status,
                    }
            return index

    async def admin_list_requests(
        self, status: str | None = None
    ) -> list[dict[str, Any]]:
        def run() -> list[dict[str, Any]]:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                return [
                    self._request_payload(row)  # type: ignore[misc]
                    for row in repo.list_requests(status)
                ]

        return await asyncio.to_thread(run)

    async def admin_set_request_status(
        self, request_id: int, status: str, admin_note: str | None = None
    ) -> dict[str, Any]:
        if status not in VALID_REQUEST_STATES:
            raise GrowlyError("Недопустимый статус заявки.")

        def run() -> dict[str, Any] | None:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                request = repo.update_request_status(
                    request_id, status, admin_note=admin_note
                )
                return self._request_payload(request)

        payload = await asyncio.to_thread(run)
        if payload is None:
            raise GrowlyError("Заявка не найдена.")
        return payload

    async def admin_link_account(
        self,
        *,
        external_account_id: str,
        request_id: int | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Link a Blotato account id to a workspace (and resolve its request)."""
        account = await self.blotato.get_account(external_account_id)
        if account is None:
            raise GrowlyError(
                "Аккаунт с таким ID не найден в Blotato. "
                "Обновите список аккаунтов."
            )
        platform = account.get("platform") or "instagram"

        def run() -> dict[str, Any]:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                target_workspace = workspace_id
                request_ref: int | None = request_id
                if request_id is not None:
                    request = repo.get_request(request_id)
                    if request is None:
                        raise GrowlyError("Заявка не найдена.")
                    target_workspace = request.workspace_id
                    platform_slug = request.platform or platform
                else:
                    platform_slug = platform
                if not target_workspace:
                    raise GrowlyError(
                        "Укажите заявку или workspace для связывания."
                    )
                linked = repo.link_account(
                    workspace_id=target_workspace,
                    platform=platform_slug,
                    external_account_id=str(account.get("id")),
                    username=account.get("name") or account.get("username"),
                    display_name=account.get("display_name"),
                    connection_request_id=request_ref,
                )
                if request_id is not None:
                    repo.update_request_status(
                        request_id,
                        "connected",
                        admin_note="Связан с Blotato аккаунтом.",
                    )
                return self._account_payload(linked)  # type: ignore[return-value]

        return await asyncio.to_thread(run)

    async def admin_unlink_account(
        self, workspace_id: str, platform: str = "instagram"
    ) -> dict[str, Any]:
        def run() -> dict[str, Any] | None:
            with session_scope() as session:
                repo = IntegrationsRepository(session)
                account = repo.unlink_account(workspace_id, platform)
                return self._account_payload(account)

        payload = await asyncio.to_thread(run)
        return {"ok": True, "account": payload}
