from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import session_scope
from app.models import (
    Approval,
    ContentPlan,
    Draft,
    MarketScanJob,
    Publication,
    Report,
    ReviewImport,
    Setting,
    Source,
    SourceItem,
)
from app.services.notion_service import NotionService
from app.utils.errors import ConfigurationError, NotionServiceError


@dataclass(frozen=True, slots=True)
class NotionArchiveTarget:
    database_name: str
    row_id: int
    page_id: str | None


@dataclass(frozen=True, slots=True)
class BusinessContextResetResult:
    deleted_counts: dict[str, int]
    notion_archived: int
    notion_missing: int
    notion_failed: int

    @property
    def deleted_total(self) -> int:
        return sum(self.deleted_counts.values())


class BusinessContextService:
    def __init__(self, notion: NotionService | None = None) -> None:
        self.notion = notion or NotionService()

    async def reset(self) -> BusinessContextResetResult:
        targets, deleted_counts = await asyncio.to_thread(
            self._delete_database_context
        )
        archived, missing, failed = await self._archive_notion_targets(targets)
        return BusinessContextResetResult(
            deleted_counts=deleted_counts,
            notion_archived=archived,
            notion_missing=missing,
            notion_failed=failed,
        )

    @classmethod
    def _delete_database_context(
        cls,
    ) -> tuple[list[NotionArchiveTarget], dict[str, int]]:
        with session_scope() as session:
            targets = cls._load_notion_targets(session)
            counts = cls._delete_rows(session)
            return targets, counts

    @staticmethod
    def _load_notion_targets(session: Session) -> list[NotionArchiveTarget]:
        model_specs: tuple[tuple[type[Any], str], ...] = (
            (Source, "Sources"),
            (SourceItem, "Source Items"),
            (ContentPlan, "Content Calendar"),
            (Draft, "Drafts"),
            (Report, "Reports"),
            (ReviewImport, "Reviews and Market Insights"),
        )
        targets: list[NotionArchiveTarget] = []
        for model, database_name in model_specs:
            rows = session.execute(
                select(model.id, model.notion_page_id)
            ).all()
            targets.extend(
                NotionArchiveTarget(
                    database_name=database_name,
                    row_id=int(row_id),
                    page_id=str(page_id) if page_id else None,
                )
                for row_id, page_id in rows
            )
        publication_ids = session.scalars(select(Publication.id)).all()
        targets.extend(
            NotionArchiveTarget(
                database_name="Publications",
                row_id=int(row_id),
                page_id=None,
            )
            for row_id in publication_ids
        )
        return targets

    @staticmethod
    def _delete_rows(session: Session) -> dict[str, int]:
        delete_specs = (
            ("approvals", delete(Approval)),
            ("market_scan_jobs", delete(MarketScanJob)),
            ("publications", delete(Publication)),
            ("drafts", delete(Draft)),
            ("content_plan", delete(ContentPlan)),
            ("source_items", delete(SourceItem)),
            ("sources", delete(Source)),
            ("reviews_imports", delete(ReviewImport)),
            ("reports", delete(Report)),
            (
                "business_settings",
                delete(Setting).where(Setting.key.like("business_%")),
            ),
        )
        counts: dict[str, int] = {}
        for label, statement in delete_specs:
            result = session.execute(statement)
            counts[label] = max(int(result.rowcount or 0), 0)
        return counts

    async def _archive_notion_targets(
        self,
        targets: list[NotionArchiveTarget],
    ) -> tuple[int, int, int]:
        semaphore = asyncio.Semaphore(2)

        async def archive(target: NotionArchiveTarget) -> str:
            async with semaphore:
                try:
                    archived = await self.notion.archive_database_row(
                        target.database_name,
                        target.row_id,
                        page_id=target.page_id,
                    )
                    return "archived" if archived else "missing"
                except (ConfigurationError, NotionServiceError):
                    return "failed"

        outcomes = await asyncio.gather(*(archive(target) for target in targets))
        return (
            outcomes.count("archived"),
            outcomes.count("missing"),
            outcomes.count("failed"),
        )
