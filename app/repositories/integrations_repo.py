from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Integration,
    ManualPublishPackage,
    Publication,
    PublicationTarget,
    SocialAccount,
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
        for existing in self.list_accounts(workspace_id, provider):
            self.session.delete(existing)
        self.session.flush()
        rows: list[SocialAccount] = []
        for account in accounts:
            row = SocialAccount(
                workspace_id=workspace_id,
                provider=provider,
                platform=str(account.get("platform") or "").strip().lower() or None,
                external_account_id=str(account.get("id") or "") or None,
                display_name=account.get("display_name"),
                username=account.get("name"),
                status="connected" if account.get("connected", True) else "error",
                metadata_json={},
            )
            self.session.add(row)
            rows.append(row)
        self.session.flush()
        return rows

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
