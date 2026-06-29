from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Source, SourceItem
from app.search.base import SearchResult


class SourcesRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_sources(self, *, active_only: bool = True) -> list[Source]:
        statement = select(Source).order_by(Source.priority, Source.name)
        if active_only:
            statement = statement.where(Source.status == "active")
        return list(self.session.scalars(statement))

    def count_sources(self, *, active_only: bool = True) -> int:
        statement = select(func.count(Source.id))
        if active_only:
            statement = statement.where(Source.status == "active")
        return int(self.session.scalar(statement) or 0)

    def get(self, source_id: int) -> Source | None:
        return self.session.get(Source, source_id)

    def find(self, value: str) -> Source | None:
        clean = value.strip()
        if clean.isdigit():
            source = self.get(int(clean))
            if source:
                return source
        return self.session.scalar(
            select(Source)
            .where(func.lower(Source.name) == clean.lower())
            .order_by(desc(Source.updated_at))
        )

    def create_source(
        self,
        *,
        name: str,
        source_type: str,
        url: str | None = None,
        category: str | None = None,
        priority: str = "medium",
        check_frequency: str = "weekly",
        notes: str | None = None,
        status: str = "active",
    ) -> Source:
        source = Source(
            name=name,
            source_type=source_type,
            url=url,
            category=category,
            priority=priority,
            check_frequency=check_frequency,
            notes=notes,
            status=status,
        )
        self.session.add(source)
        self.session.flush()
        return source

    def find_by_url(self, url: str) -> Source | None:
        clean = url.strip().rstrip("/")
        if not clean:
            return None
        return self.session.scalar(
            select(Source)
            .where(func.lower(func.rtrim(Source.url, "/")) == clean.lower())
            .order_by(desc(Source.updated_at))
        )

    def create_discovered_source(
        self,
        *,
        name: str,
        source_type: str,
        url: str,
        category: str,
        notes: str,
    ) -> tuple[Source, bool]:
        existing = self.find_by_url(url)
        if existing:
            return existing, False
        return (
            self.create_source(
                name=name,
                source_type=source_type,
                url=url,
                category=category,
                priority="medium",
                check_frequency="weekly",
                notes=notes,
                status="requires_review",
            ),
            True,
        )

    def set_status(self, source: Source, status: str) -> Source:
        source.status = status
        self.session.flush()
        return source

    def disable(self, source: Source) -> Source:
        return self.set_status(source, "disabled")

    def create_item(
        self,
        *,
        source_id: int,
        title: str | None,
        raw_text: str,
        external_url: str | None = None,
        metrics: dict | None = None,
        tags: list | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> SourceItem:
        insight = analysis or {}
        source = self.get(source_id)
        clean_title = (title or "Untitled source item").strip()
        clean_url = (external_url or "").strip()
        item = SourceItem(
            source_id=source_id,
            source_name=source.name if source else None,
            source_type=source.source_type or "manual" if source else "manual",
            source_provider="manual",
            query=f"source:{source_id}",
            title=clean_title,
            url=clean_url,
            raw_text=raw_text,
            content=raw_text,
            external_url=clean_url or None,
            metrics_json=metrics or {},
            ai_summary=insight.get("summary"),
            topic=insight.get("topic"),
            content_format=insight.get("content_format"),
            offer=insight.get("offer"),
            cta=insight.get("cta"),
            audience_pain=insight.get("audience_pain"),
            hook=insight.get("hook"),
            engagement_signals_json=insight.get("engagement_signals") or {},
            risk_warning=insight.get("risk_warning"),
            adaptation_idea=insight.get("adaptation_idea"),
            tags_json=tags or [],
        )
        self.session.add(item)
        if source:
            source.last_checked_at = datetime.now(UTC)
        self.session.flush()
        return item

    def create_search_item(self, result: SearchResult) -> SourceItem:
        item = SourceItem(
            source_name=result.title,
            source_type="web_search",
            source_provider=result.source_provider,
            query=result.query,
            title=result.title,
            url=result.url,
            external_url=result.url,
            snippet=result.snippet,
            content=result.content,
            raw_text=result.content or result.snippet,
            published_at=self._parse_datetime(result.published_at),
            score=result.score,
            raw_json=result.raw_json,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def create_monitoring_item(
        self,
        source: Source,
        result: SearchResult,
    ) -> SourceItem:
        item = SourceItem(
            source_id=source.id,
            source_name=source.name,
            source_type="source_monitoring",
            source_provider=result.source_provider,
            query=result.query,
            title=result.title,
            url=result.url,
            external_url=result.url,
            snippet=result.snippet,
            content=result.content,
            raw_text=result.content or result.snippet,
            published_at=self._parse_datetime(result.published_at),
            score=result.score,
            raw_json=result.raw_json,
        )
        self.session.add(item)
        source.last_checked_at = datetime.now(UTC)
        self.session.flush()
        return item

    def list_search_items(self, limit: int = 200) -> list[SourceItem]:
        return list(
            self.session.scalars(
                select(SourceItem)
                .where(SourceItem.source_type == "web_search")
                .order_by(desc(SourceItem.created_at))
                .limit(limit)
            )
        )

    def has_search_items(self) -> bool:
        return bool(
            self.session.scalar(
                select(func.count(SourceItem.id)).where(
                    SourceItem.source_type == "web_search"
                )
            )
        )

    def update_search_item_analysis(
        self,
        item: SourceItem,
        analysis: dict[str, Any],
    ) -> SourceItem:
        item.ai_summary = str(analysis.get("ai_summary") or "").strip() or None
        item.topics_json = self._as_list(analysis.get("topics"))
        item.offers_json = self._as_list(analysis.get("offers"))
        item.ctas_json = self._as_list(analysis.get("ctas"))
        item.pains_json = self._as_list(analysis.get("pains"))
        item.objections_json = self._as_list(analysis.get("objections"))
        item.content_gaps_json = self._as_list(analysis.get("content_gaps"))
        item.ideas_json = self._as_list(analysis.get("ideas"))
        self.session.flush()
        return item

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def list_recent_items(self, limit: int = 100) -> list[SourceItem]:
        statement = (
            select(SourceItem)
            .options(joinedload(SourceItem.source))
            .order_by(desc(SourceItem.collected_at))
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_items_for_source(self, source_id: int, limit: int = 100) -> list[SourceItem]:
        return list(
            self.session.scalars(
                select(SourceItem)
                .where(SourceItem.source_id == source_id)
                .order_by(desc(SourceItem.collected_at))
                .limit(limit)
            )
        )

    def search_sources(self, value: str, limit: int = 20) -> list[Source]:
        pattern = f"%{value.strip()}%"
        return list(
            self.session.scalars(
                select(Source)
                .where(
                    or_(
                        Source.name.ilike(pattern),
                        Source.url.ilike(pattern),
                    )
                )
                .order_by(Source.name)
                .limit(limit)
            )
        )
