from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select

from app.database import session_scope
from app.models import Draft, Publication, Report, ReviewImport, Setting, Source, SourceItem
from app.repositories.reports_repo import ReportsRepository
from app.repositories.sources_repo import SourcesRepository
from app.services.ai_service import AIService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notion_service import NotionService
from app.source_collectors.manual_collector import ManualCollector
from app.utils.errors import NotionServiceError
from app.utils.errors import AIServiceError
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)


def current_week() -> tuple[date, date]:
    today = datetime.now(UTC).date()
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


class SourceAnalysisService:
    def __init__(
        self,
        groq: AIService | None = None,
        notion: NotionService | None = None,
    ) -> None:
        self.groq = groq or AIService()
        self.notion = notion or NotionService()
        self.manual_collector = ManualCollector()

    async def add_source(
        self,
        *,
        name: str,
        source_type: str,
        url: str,
        category: str,
        priority: str,
        check_frequency: str,
        workspace_id: str | None = None,
    ) -> Source:
        def save() -> Source:
            with session_scope() as session:
                return SourcesRepository(session).create_source(
                    name=name.strip(),
                    workspace_id=workspace_id,
                    source_type=source_type.strip(),
                    url=url.strip() or None,
                    category=category.strip(),
                    priority=priority.strip(),
                    check_frequency=check_frequency.strip(),
                )

        source = await asyncio.to_thread(save)
        try:
            page = await self.notion.sync_source(source)
            await asyncio.to_thread(self._save_source_page_id, source.id, page["id"])
            source.notion_page_id = page["id"]
        except NotionServiceError:
            logger.warning("Source %s could not sync to Notion.", source.id)
        return source

    async def list_sources(
        self, *, active_only: bool = True, workspace_id: str | None = None
    ) -> list[Source]:
        def load() -> list[Source]:
            with session_scope() as session:
                return SourcesRepository(session).list_sources(
                    active_only=active_only,
                    workspace_id=workspace_id,
                )

        return await asyncio.to_thread(load)

    async def find_source(
        self, value: str, workspace_id: str | None = None
    ) -> Source | None:
        def load() -> Source | None:
            with session_scope() as session:
                return SourcesRepository(session).find(
                    value, workspace_id=workspace_id
                )

        return await asyncio.to_thread(load)

    async def disable_source(self, value: str) -> Source:
        def update() -> Source:
            with session_scope() as session:
                repo = SourcesRepository(session)
                source = repo.find(value)
                if source is None:
                    raise ValueError("Source was not found.")
                return repo.disable(source)

        source = await asyncio.to_thread(update)
        try:
            await self.notion.sync_source(source)
        except NotionServiceError:
            logger.warning("Disabled source %s could not sync to Notion.", source.id)
        return source

    @staticmethod
    def split_import_text(raw_text: str, *, max_items: int = 30) -> list[str]:
        clean = raw_text.strip()
        if not clean:
            return []
        blocks = [
            block.strip()
            for block in re.split(r"\n\s*(?:---+|===+)\s*\n|\n{2,}", clean)
            if block.strip()
        ]
        if len(blocks) == 1:
            numbered = re.split(r"\n(?=\s*(?:\d+[.)]|[-*]\s+))", clean)
            if len(numbered) > 1:
                blocks = [block.strip() for block in numbered if block.strip()]
        return blocks[:max_items]

    async def import_source_items(
        self, *, source_id: int, raw_text: str
    ) -> list[SourceItem]:
        items = self.split_import_text(raw_text)
        if not items:
            raise ValueError("No source items were found in the supplied text.")
        source = await self.find_source(str(source_id))
        if source is None:
            raise ValueError("Source was not found.")
        response = await self.groq.analyze_source_items(
            {
                "source": {
                    "id": source.id,
                    "name": source.name,
                    "type": source.source_type,
                    "category": source.category,
                },
                "items": [
                    {"item_number": index, "raw_text": text}
                    for index, text in enumerate(items, start=1)
                ],
            }
        )
        payload = parse_json_response(response)
        if not isinstance(payload, list) or len(payload) != len(items):
            raise AIServiceError(
                "Source item analysis did not return one result per imported item."
            )

        def save() -> list[SourceItem]:
            with session_scope() as session:
                repo = SourcesRepository(session)
                saved: list[SourceItem] = []
                for index, raw_item in enumerate(items):
                    analysis = payload[index]
                    if not isinstance(analysis, dict):
                        raise AIServiceError("A source item analysis result is invalid.")
                    tags = analysis.get("tags")
                    engagement = analysis.get("engagement_signals")
                    saved.append(
                        repo.create_item(
                            source_id=source_id,
                            title=str(analysis.get("topic") or f"Imported item {index + 1}"),
                            raw_text=raw_item,
                            metrics=engagement if isinstance(engagement, dict) else {},
                            tags=tags if isinstance(tags, list) else [],
                            analysis=analysis,
                        )
                    )
                return saved

        saved_items = await asyncio.to_thread(save)
        for item in saved_items:
            try:
                page = await self.notion.sync_source_item(item)
                await asyncio.to_thread(self._save_source_item_page_id, item.id, page["id"])
                item.notion_page_id = page["id"]
            except NotionServiceError:
                logger.warning("Source item %s could not sync to Notion.", item.id)
        return saved_items

    async def add_manual_item(
        self,
        *,
        source_id: int,
        raw_text: str,
        title: str | None = None,
        external_url: str | None = None,
    ) -> int:
        collected = await self.manual_collector.collect(
            raw_text=raw_text, title=title, external_url=external_url
        )

        def save() -> int:
            with session_scope() as session:
                repo = SourcesRepository(session)
                if repo.get(source_id) is None:
                    raise ValueError("Source was not found.")
                item = repo.create_item(
                    source_id=source_id,
                    title=collected[0].title,
                    raw_text=collected[0].raw_text,
                    external_url=collected[0].external_url,
                    metrics=collected[0].metrics,
                    tags=collected[0].tags,
                )
                return item.id

        return await asyncio.to_thread(save)

    async def generate_competitor_report(
        self, query: str | None = None
    ) -> Report:
        return await MarketIntelligenceService(
            groq=self.groq,
            notion=self.notion,
        ).generate_competitor_report(query=query)

    @staticmethod
    def _build_context() -> dict[str, Any]:
        with session_scope() as session:
            repo = SourcesRepository(session)
            sources = repo.list_sources(active_only=False)
            items = repo.list_recent_items(limit=100)
            reviews = list(
                session.scalars(
                    select(ReviewImport).order_by(desc(ReviewImport.created_at)).limit(20)
                )
            )
            publications = list(
                session.scalars(
                    select(Publication)
                    .order_by(desc(Publication.created_at))
                    .limit(50)
                )
            )
            drafts = list(
                session.scalars(select(Draft).order_by(desc(Draft.created_at)).limit(50))
            )
            business_settings = list(
                session.scalars(
                    select(Setting)
                    .where(Setting.key.like("business_%"))
                    .order_by(Setting.key)
                )
            )
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "data_limited": not bool(items),
                "sources": [
                    {
                        "id": source.id,
                        "name": source.name,
                        "type": source.source_type,
                        "category": source.category,
                        "url": source.url,
                        "priority": source.priority,
                        "status": source.status,
                        "check_frequency": source.check_frequency,
                        "notes": source.notes,
                    }
                    for source in sources
                ],
                "source_items": [
                    {
                        "source": item.source.name if item.source else None,
                        "title": item.title,
                        "text": item.raw_text,
                        "summary": item.ai_summary,
                        "topic": item.topic,
                        "format": item.content_format,
                        "offer": item.offer,
                        "cta": item.cta,
                        "pain": item.audience_pain,
                        "hook": item.hook,
                        "adaptation_idea": item.adaptation_idea,
                        "risk_warning": item.risk_warning,
                        "metrics": item.metrics_json,
                        "published_at": item.published_at,
                        "collected_at": item.collected_at,
                    }
                    for item in items
                ],
                "review_insights": [
                    {
                        "summary": row.ai_summary,
                        "pains": row.pains_json,
                        "objections": row.objections_json,
                        "questions": row.repeated_questions_json,
                        "trust_issues": row.trust_issues_json,
                        "buying_triggers": row.buying_triggers_json,
                        "customer_language": row.customer_language_json,
                    }
                    for row in reviews
                ],
                "publication_history": [
                    {
                        "draft_id": row.draft_id,
                        "status": row.status,
                        "views": row.views,
                        "reactions": row.reactions,
                        "comments": row.comments_count,
                        "clicks": row.clicks,
                        "leads": row.leads,
                    }
                    for row in publications
                ],
                "draft_history": [
                    {
                        "type": row.draft_type,
                        "channel": row.channel,
                        "title": row.title,
                        "status": row.status,
                    }
                    for row in drafts
                ],
                "business_settings": {
                    row.key: row.value for row in business_settings
                },
            }

    @staticmethod
    def _save_page_id(report_id: int, page_id: str) -> None:
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report:
                report.notion_page_id = page_id

    @staticmethod
    def _save_source_page_id(source_id: int, page_id: str) -> None:
        with session_scope() as session:
            source = session.get(Source, source_id)
            if source:
                source.notion_page_id = page_id

    @staticmethod
    def _save_source_item_page_id(item_id: int, page_id: str) -> None:
        with session_scope() as session:
            item = session.get(SourceItem, item_id)
            if item:
                item.notion_page_id = page_id
