from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Integration,
    ManualPublishPackage,
    Publication,
    PublicationTarget,
    SocialAccount,
    SocialConnectionRequest,
)


class IntegrationsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -- integrations ------------------------------------------------------

    def get_integration(
        self, workspace_id: str | None, provider: str
    ) -> Integration | None:
        return self.session.scalar(
            select(Integration).where(
                Integration.workspace_id == workspace_id,
                Integration.provider == provider,
            )
        )

    def upsert_integration(
        self,
        *,
        workspace_id: str | None,
        provider: str,
        enabled: bool,
        status: str | None,
        metadata: dict[str, Any] | None = None,
        last_checked_at: datetime | None = None,
    ) -> Integration:
        integration = self.get_integration(workspace_id, provider)
        if integration is None:
            integration = Integration(workspace_id=workspace_id, provider=provider)
            self.session.add(integration)
        integration.enabled = enabled
        integration.status = status
        if metadata is not None:
            integration.metadata_json = metadata
        if last_checked_at is not None:
            integration.last_checked_at = last_checked_at
        self.session.flush()
        return integration

    def set_api_key(
        self,
        *,
        workspace_id: str | None,
        provider: str,
        api_key_encrypted: str | None,
        status: str | None = None,
        enabled: bool | None = None,
    ) -> Integration:
        integration = self.get_integration(workspace_id, provider)
        if integration is None:
            integration = Integration(workspace_id=workspace_id, provider=provider)
            self.session.add(integration)
        integration.api_key_encrypted = api_key_encrypted
        if status is not None:
            integration.status = status
        if enabled is not None:
            integration.enabled = enabled
        self.session.flush()
        return integration

    def get_api_key_ref(
        self, workspace_id: str | None, provider: str
    ) -> str | None:
        integration = self.get_integration(workspace_id, provider)
        return integration.api_key_encrypted if integration else None

    # -- social accounts ---------------------------------------------------

    def list_accounts(
        self, workspace_id: str | None, provider: str
    ) -> list[SocialAccount]:
        return list(
            self.session.scalars(
                select(SocialAccount)
                .where(
                    SocialAccount.workspace_id == workspace_id,
                    SocialAccount.provider == provider,
                )
                .order_by(SocialAccount.platform, SocialAccount.id)
            )
        )

    def replace_accounts(
        self,
        *,
        workspace_id: str | None,
        provider: str,
        accounts: list[dict[str, Any]],
    ) -> list[SocialAccount]:
        existing_rows = self.list_accounts(workspace_id, provider)
        by_external_id = {
            row.external_account_id: row
            for row in existing_rows
            if row.external_account_id
        }
        rows: list[SocialAccount] = []
        seen_ids: set[str] = set()
        for account in accounts:
            external_id = str(account.get("id") or "").strip()
            if not external_id:
                continue
            seen_ids.add(external_id)
            row = by_external_id.get(external_id)
            if row is None:
                row = SocialAccount(
                    workspace_id=workspace_id,
                    provider=provider,
                    external_account_id=external_id,
                    metadata_json={},
                )
                self.session.add(row)
            row.platform = (
                str(account.get("platform") or "").strip().lower() or None
            )
            row.display_name = account.get("display_name")
            row.username = account.get("name")
            row.status = "connected" if account.get("connected", True) else "error"
            row.metadata_json = {
                **(row.metadata_json or {}),
                "subaccounts": account.get("subaccounts") or [],
            }
            row.last_checked_at = datetime.now(UTC)
            rows.append(row)
        for row in existing_rows:
            if row.external_account_id and row.external_account_id not in seen_ids:
                row.status = "disconnected"
                row.last_checked_at = datetime.now(UTC)
        self.session.flush()
        return rows

    def connected_account(
        self, workspace_id: str | None, platform: str, provider: str = "blotato"
    ) -> SocialAccount | None:
        return self.session.scalar(
            select(SocialAccount)
            .where(
                SocialAccount.workspace_id == workspace_id,
                SocialAccount.provider == provider,
                SocialAccount.platform == platform.strip().lower(),
                SocialAccount.status == "connected",
            )
            .order_by(desc(SocialAccount.id))
        )

    def link_account(
        self,
        *,
        workspace_id: str | None,
        platform: str,
        external_account_id: str,
        username: str | None,
        display_name: str | None,
        connection_request_id: int | None = None,
        provider: str = "blotato",
    ) -> SocialAccount:
        """Create or update the connected account for a workspace+platform."""
        slug = platform.strip().lower()
        account = self.session.scalar(
            select(SocialAccount).where(
                SocialAccount.workspace_id == workspace_id,
                SocialAccount.provider == provider,
                SocialAccount.platform == slug,
            )
        )
        if account is None:
            account = SocialAccount(
                workspace_id=workspace_id, provider=provider, platform=slug
            )
            self.session.add(account)
        account.external_account_id = external_account_id
        account.username = username
        account.display_name = display_name
        account.status = "connected"
        account.connection_request_id = connection_request_id
        account.connected_at = datetime.now(UTC)
        account.last_checked_at = datetime.now(UTC)
        self.session.flush()
        return account

    def unlink_account(
        self, workspace_id: str | None, platform: str, provider: str = "blotato"
    ) -> SocialAccount | None:
        account = self.session.scalar(
            select(SocialAccount).where(
                SocialAccount.workspace_id == workspace_id,
                SocialAccount.provider == provider,
                SocialAccount.platform == platform.strip().lower(),
            )
        )
        if account is not None:
            account.status = "disconnected"
            self.session.flush()
        return account

    def mark_account_checked(self, account: SocialAccount) -> SocialAccount:
        account.last_checked_at = datetime.now(UTC)
        self.session.flush()
        return account

    # -- social connection requests ---------------------------------------

    def create_request(
        self,
        *,
        workspace_id: str | None,
        user_email: str | None,
        platform: str,
        requested_username: str | None,
        user_note: str | None = None,
    ) -> SocialConnectionRequest:
        request = SocialConnectionRequest(
            workspace_id=workspace_id,
            user_email=user_email,
            platform=platform.strip().lower(),
            requested_username=requested_username,
            user_note=user_note,
            status="pending",
        )
        self.session.add(request)
        self.session.flush()
        return request

    def get_request(self, request_id: int) -> SocialConnectionRequest | None:
        return self.session.get(SocialConnectionRequest, request_id)

    def latest_request(
        self, workspace_id: str | None, platform: str
    ) -> SocialConnectionRequest | None:
        return self.session.scalar(
            select(SocialConnectionRequest)
            .where(
                SocialConnectionRequest.workspace_id == workspace_id,
                SocialConnectionRequest.platform == platform.strip().lower(),
            )
            .order_by(desc(SocialConnectionRequest.created_at))
        )

    def list_requests(
        self, status: str | None = None
    ) -> list[SocialConnectionRequest]:
        statement = select(SocialConnectionRequest).order_by(
            desc(SocialConnectionRequest.created_at)
        )
        if status:
            statement = statement.where(
                SocialConnectionRequest.status == status
            )
        return list(self.session.scalars(statement))

    def update_request_status(
        self,
        request_id: int,
        status: str,
        *,
        admin_note: str | None = None,
    ) -> SocialConnectionRequest | None:
        request = self.get_request(request_id)
        if request is None:
            return None
        request.status = status
        if admin_note is not None:
            request.admin_note = admin_note
        if status in {"connected", "cancelled", "failed"}:
            request.resolved_at = datetime.now(UTC)
        self.session.flush()
        return request

    # -- publication targets (platform -> account mappings) ----------------

    def list_targets(self, workspace_id: str | None) -> list[PublicationTarget]:
        return list(
            self.session.scalars(
                select(PublicationTarget)
                .where(PublicationTarget.workspace_id == workspace_id)
                .order_by(PublicationTarget.platform)
            )
        )

    def get_target(
        self, workspace_id: str | None, platform: str
    ) -> PublicationTarget | None:
        return self.session.scalar(
            select(PublicationTarget).where(
                PublicationTarget.workspace_id == workspace_id,
                PublicationTarget.platform == platform.strip().lower(),
            )
        )

    def set_mapping(
        self,
        *,
        workspace_id: str | None,
        platform: str,
        account_id: str | None,
        page_id: str | None = None,
        provider: str = "blotato",
        enabled: bool = True,
    ) -> PublicationTarget:
        target = self.get_target(workspace_id, platform)
        if target is None:
            target = PublicationTarget(
                workspace_id=workspace_id,
                platform=platform.strip().lower(),
            )
            self.session.add(target)
        target.provider = provider
        target.account_id = account_id
        target.page_id = page_id
        target.enabled = enabled
        self.session.flush()
        return target

    def clear_mappings(
        self,
        workspace_id: str | None,
        provider: str = "blotato",
    ) -> None:
        for target in self.list_targets(workspace_id):
            if target.provider != provider:
                continue
            target.account_id = None
            target.page_id = None
            target.enabled = False
        self.session.flush()

    # -- publications ------------------------------------------------------

    def create_publication(self, **fields: Any) -> Publication:
        publication = Publication(**fields)
        self.session.add(publication)
        self.session.flush()
        return publication

    def get_publication(self, publication_id: int) -> Publication | None:
        return self.session.get(Publication, publication_id)

    # -- manual publish packages ------------------------------------------

    def upsert_manual_package(
        self,
        *,
        workspace_id: str | None,
        draft_id: int | None,
        platform: str,
        caption: str | None,
        hook: str | None,
        script: str | None,
        visual_brief: str | None,
        hashtags: str | None,
        cta: str | None,
    ) -> ManualPublishPackage:
        package = self.session.scalar(
            select(ManualPublishPackage).where(
                ManualPublishPackage.workspace_id == workspace_id,
                ManualPublishPackage.draft_id == draft_id,
                ManualPublishPackage.platform == platform.strip().lower(),
            )
        )
        if package is None:
            package = ManualPublishPackage(
                workspace_id=workspace_id,
                draft_id=draft_id,
                platform=platform.strip().lower(),
            )
            self.session.add(package)
        package.caption = caption
        package.hook = hook
        package.script = script
        package.visual_brief = visual_brief
        package.hashtags = hashtags
        package.cta = cta
        package.status = "ready"
        self.session.flush()
        return package

    def list_manual_packages(
        self, workspace_id: str | None, draft_id: int
    ) -> list[ManualPublishPackage]:
        return list(
            self.session.scalars(
                select(ManualPublishPackage)
                .where(
                    ManualPublishPackage.workspace_id == workspace_id,
                    ManualPublishPackage.draft_id == draft_id,
                )
                .order_by(desc(ManualPublishPackage.updated_at))
            )
        )
