from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import Report, Source, SourceItem
from app.repositories.reports_repo import ReportsRepository
from app.repositories.sources_repo import SourcesRepository
from app.search.base import BaseSearchProvider, SearchResult
from app.search.factory import get_search_provider
from app.services.ai_service import AIService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notion_service import NotionService
from app.utils.errors import (
    AIServiceError,
    NotionServiceError,
    SearchServiceError,
)
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = {
    "website": "Website",
    "telegram": "Telegram",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
}

PLATFORM_DOMAINS = {
    "Telegram": ("t.me", "telegram.me"),
    "Instagram": ("instagram.com",),
    "TikTok": ("tiktok.com",),
    "YouTube": ("youtube.com", "youtu.be"),
}

PLATFORM_LIMITATIONS = {
    "Website": "Public website discovery and public web evidence only.",
    "Telegram": (
        "Public-channel discovery only. Full post collection requires a separate "
        "public Telegram collector."
    ),
    "Instagram": (
        "Tavily discovery/search evidence only; this is not full Instagram monitoring."
    ),
    "TikTok": (
        "Tavily discovery/search evidence only; this is not full TikTok monitoring."
    ),
    "YouTube": (
        "Tavily discovery/search evidence only. YouTube Shorts metrics require "
        "the YouTube Data API."
    ),
}


class SourceDiscoveryService:
    def __init__(
        self,
        settings: Settings | None = None,
        search_provider: BaseSearchProvider | None = None,
        groq: AIService | None = None,
        notion: NotionService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.search_provider = search_provider
        self.groq = groq or AIService(self.settings)
        self.notion = notion or NotionService(self.settings)

    def _provider(self) -> BaseSearchProvider:
        if self.search_provider is None:
            self.search_provider = get_search_provider(self.settings)
        return self.search_provider

    async def discover_sources(
        self,
        *,
        niche: str,
        region: str,
        platforms: list[str],
    ) -> list[Source]:
        normalized_platforms = self.normalize_platforms(platforms)
        queries = self.build_discovery_queries(
            niche=niche,
            region=region,
            platforms=normalized_platforms,
        )
        search_results: list[SearchResult] = []
        for platform, query in queries:
            results = await asyncio.to_thread(
                self._provider().search,
                query,
                min(self.settings.search_max_results, 8),
                include_raw_content=False,
            )
            search_results.extend(
                result
                for result in results
                if self.result_matches_platform(result.url, platform)
            )
        unique_results = self._deduplicate_results(search_results)
        candidates = await self._extract_candidates(
            niche=niche,
            region=region,
            platforms=normalized_platforms,
            results=unique_results,
        )
        saved = await asyncio.to_thread(
            self._save_candidates,
            niche,
            candidates,
        )
        await self._sync_sources(saved)
        return saved

    async def monitor_active_sources(self) -> tuple[Report, list[SourceItem]]:
        sources = await asyncio.to_thread(self._load_active_sources)
        if not sources:
            raise ValueError(
                "Нет активных источников. Сначала используйте /discover_sources "
                "и подтвердите нужные источники."
            )

        findings: list[tuple[int, SearchResult]] = []
        failures: list[str] = []
        for source in sources:
            query = self.build_monitoring_query(source)
            try:
                results = await asyncio.to_thread(
                    self._provider().search,
                    query,
                    min(self.settings.search_max_results, 3),
                    include_raw_content=False,
                )
            except SearchServiceError:
                failures.append(source.name)
                continue
            findings.extend((source.id, result) for result in results)

        saved_items = await asyncio.to_thread(self._save_monitoring_findings, findings)
        summary = await self._summarize_monitoring(
            sources=sources,
            saved_items=saved_items,
            failed_sources=failures,
        )
        saved_items = await asyncio.to_thread(
            self._apply_finding_summaries,
            [item.id for item in saved_items],
        )
        await self._sync_source_items(saved_items)
        report = await asyncio.to_thread(
            self._save_monitoring_report,
            summary,
            len(sources),
            len(saved_items),
        )
        await self._sync_report(report)
        sources = await asyncio.to_thread(self._load_active_sources)
        await self._sync_sources(sources)
        return report, saved_items

    async def approve_source(self, source_id: int) -> Source:
        source = await asyncio.to_thread(self._set_source_status, source_id, "active")
        await self._sync_sources([source])
        return source

    async def disable_source(self, source_id: int) -> Source:
        source = await asyncio.to_thread(
            self._set_source_status, source_id, "disabled"
        )
        await self._sync_sources([source])
        return source

    @staticmethod
    def normalize_platforms(platforms: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in platforms:
            key = value.strip().lower()
            if key in SUPPORTED_PLATFORMS:
                label = SUPPORTED_PLATFORMS[key]
                if label not in normalized:
                    normalized.append(label)
        if not normalized:
            raise ValueError(
                "Укажите хотя бы одну платформу: website, Telegram, Instagram, "
                "TikTok или YouTube."
            )
        return normalized

    @staticmethod
    def build_discovery_queries(
        *,
        niche: str,
        region: str,
        platforms: list[str],
    ) -> list[tuple[str, str]]:
        clean_niche = niche.strip()
        clean_region = region.strip()
        queries: list[tuple[str, str]] = []
        for platform in platforms:
            if platform == "Website":
                query = (
                    f"{clean_niche} companies competitors {clean_region} "
                    "official website"
                )
            elif platform == "Telegram":
                query = (
                    f"site:t.me {clean_niche} {clean_region} public channel business"
                )
            elif platform == "Instagram":
                query = (
                    f"site:instagram.com {clean_niche} {clean_region} official business"
                )
            elif platform == "TikTok":
                query = (
                    f"site:tiktok.com {clean_niche} {clean_region} official business"
                )
            else:
                query = (
                    f"site:youtube.com {clean_niche} {clean_region} official channel"
                )
            queries.append((platform, query))
        return queries

    @staticmethod
    def result_matches_platform(url: str, platform: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if platform == "Website":
            social_domains = {
                domain
                for domains in PLATFORM_DOMAINS.values()
                for domain in domains
            }
            return bool(host) and not any(
                host == domain or host.endswith(f".{domain}")
                for domain in social_domains
            )
        if not any(
            host == domain or host.endswith(f".{domain}")
            for domain in PLATFORM_DOMAINS[platform]
        ):
            return False
        parts = [part for part in parsed.path.split("/") if part]
        if platform == "Instagram":
            return bool(parts) and parts[0].lower() not in {
                "p",
                "reel",
                "reels",
                "stories",
                "explore",
            }
        if platform == "TikTok":
            return bool(parts) and parts[0].startswith("@") and "video" not in parts
        if platform == "YouTube":
            return (
                host != "youtu.be"
                and bool(parts)
                and (
                    parts[0].startswith("@")
                    or parts[0].lower() in {"channel", "c", "user"}
                )
            )
        if not parts:
            return False
        return not (len(parts) > 1 and parts[-1].isdigit())

    @staticmethod
    def build_monitoring_query(source: Source) -> str:
        url = (source.url or "").strip()
        return (
            f'"{source.name}" "{url}" latest public information updates '
            f"{source.source_type or 'website'}"
        ).strip()

    async def _extract_candidates(
        self,
        *,
        niche: str,
        region: str,
        platforms: list[str],
        results: list[SearchResult],
    ) -> list[dict[str, str]]:
        if not results:
            return []
        response = await self.groq.extract_source_candidates(
            {
                "niche": niche,
                "region": region,
                "requested_platforms": platforms,
                "results": [asdict(result) for result in results],
            }
        )
        payload = parse_json_response(response)
        if not isinstance(payload, list):
            raise AIServiceError("Source discovery response was not a JSON array.")

        allowed_urls = {
            self._normalize_url(result.url): result for result in results
        }
        candidates: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for row in payload:
            if not isinstance(row, dict):
                continue
            normalized_url = self._normalize_url(str(row.get("url") or ""))
            platform_value = str(row.get("platform") or "").strip()
            platform = SUPPORTED_PLATFORMS.get(
                platform_value.lower(),
                platform_value,
            )
            if (
                normalized_url not in allowed_urls
                or normalized_url in seen_urls
                or platform not in platforms
                or not self.result_matches_platform(normalized_url, platform)
            ):
                continue
            evidence = allowed_urls[normalized_url]
            name = str(row.get("name") or evidence.title).strip()
            if not name:
                continue
            candidates.append(
                {
                    "name": name[:300],
                    "url": evidence.url,
                    "platform": platform,
                    "reason": str(row.get("reason") or evidence.snippet or "").strip(),
                    "evidence_title": str(
                        row.get("evidence_title") or evidence.title
                    ).strip(),
                }
            )
            seen_urls.add(normalized_url)
        return candidates

    @staticmethod
    def _normalize_url(value: str) -> str:
        return value.strip().rstrip("/")

    @staticmethod
    def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
        unique: dict[str, SearchResult] = {}
        for result in results:
            unique.setdefault(
                SourceDiscoveryService._normalize_url(result.url),
                result,
            )
        return list(unique.values())

    @staticmethod
    def _save_candidates(
        niche: str,
        candidates: list[dict[str, str]],
    ) -> list[Source]:
        with session_scope() as session:
            repo = SourcesRepository(session)
            saved: list[Source] = []
            for candidate in candidates:
                platform = candidate["platform"]
                notes = (
                    f"Discovered via Tavily public web search. "
                    f"Evidence: {candidate['evidence_title']}. "
                    f"Reason: {candidate['reason'] or 'No additional reason supplied.'} "
                    f"Limitation: {PLATFORM_LIMITATIONS[platform]}"
                )
                source, _ = repo.create_discovered_source(
                    name=candidate["name"],
                    source_type=platform,
                    url=candidate["url"],
                    category=niche.strip(),
                    notes=notes,
                )
                saved.append(source)
            return saved

    @staticmethod
    def _load_active_sources() -> list[Source]:
        with session_scope() as session:
            return SourcesRepository(session).list_sources(active_only=True)

    @staticmethod
    def _save_monitoring_findings(
        findings: list[tuple[int, SearchResult]],
    ) -> list[SourceItem]:
        with session_scope() as session:
            repo = SourcesRepository(session)
            saved: list[SourceItem] = []
            seen: set[tuple[int, str]] = set()
            for source_id, result in findings:
                key = (source_id, SourceDiscoveryService._normalize_url(result.url))
                if key in seen:
                    continue
                source = repo.get(source_id)
                if source is None or source.status != "active":
                    continue
                saved.append(repo.create_monitoring_item(source, result))
                seen.add(key)
            return saved

    @staticmethod
    def _apply_finding_summaries(item_ids: list[int]) -> list[SourceItem]:
        if not item_ids:
            return []
        with session_scope() as session:
            items = [
                item
                for item_id in item_ids
                if (item := session.get(SourceItem, item_id)) is not None
            ]
            for item in items:
                if not item.ai_summary:
                    item.ai_summary = item.snippet
            session.flush()
            return items

    async def _summarize_monitoring(
        self,
        *,
        sources: list[Source],
        saved_items: list[SourceItem],
        failed_sources: list[str],
    ) -> dict[str, Any]:
        response = await self.groq.summarize_source_monitoring(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "sources": [
                    {
                        "id": source.id,
                        "name": source.name,
                        "type": source.source_type,
                        "url": source.url,
                    }
                    for source in sources
                ],
                "findings": [
                    MarketIntelligenceService.source_item_to_dict(item)
                    for item in saved_items
                ],
                "search_failures": failed_sources,
                "limitations": list(PLATFORM_LIMITATIONS.values()),
            }
        )
        payload = parse_json_response(response)
        if not isinstance(payload, dict):
            raise AIServiceError("Source monitoring response was not a JSON object.")
        payload["sources_checked"] = len(sources)
        payload["findings_count"] = len(saved_items)
        return payload

    @staticmethod
    def render_monitoring_summary(payload: dict[str, Any]) -> str:
        def render(title: str, value: Any) -> str:
            if isinstance(value, list):
                body = "\n".join(f"- {item}" for item in value) or "- Нет данных"
            else:
                body = str(value or "Нет данных")
            return f"{title}\n{body}"

        return "\n\n".join(
            [
                render("Краткий вывод", payload.get("executive_summary")),
                render("Заметные обновления", payload.get("notable_updates")),
                render("Повторяющиеся темы", payload.get("repeated_themes")),
                render("Риски и ограничения", payload.get("risks_and_limitations")),
                render("Источники доказательств", payload.get("evidence_urls")),
            ]
        )

    @classmethod
    def _save_monitoring_report(
        cls,
        summary: dict[str, Any],
        sources_count: int,
        findings_count: int,
    ) -> Report:
        body = cls.render_monitoring_summary(summary)
        with session_scope() as session:
            return ReportsRepository(session).create_report(
                report_type="source_monitoring",
                title=f"Source monitoring: {datetime.now(UTC).date().isoformat()}",
                report_text=body,
                summary=str(summary.get("executive_summary") or "")[:1800],
                query="active saved sources",
                sources_count=sources_count,
                evidence=(
                    summary.get("evidence_urls")
                    if isinstance(summary.get("evidence_urls"), list)
                    else []
                ),
                recommendations=(
                    summary.get("notable_updates")
                    if isinstance(summary.get("notable_updates"), list)
                    else []
                ),
                raw_json={
                    **summary,
                    "findings_count": findings_count,
                },
            )

    @staticmethod
    def _set_source_status(source_id: int, status: str) -> Source:
        with session_scope() as session:
            repo = SourcesRepository(session)
            source = repo.get(source_id)
            if source is None:
                raise ValueError("Источник не найден.")
            return repo.set_status(source, status)

    async def _sync_sources(self, sources: list[Source]) -> None:
        for source in sources:
            try:
                page = await self.notion.sync_source(source)
                if not source.notion_page_id:
                    await asyncio.to_thread(
                        self._save_source_page_id,
                        source.id,
                        page["id"],
                    )
                    source.notion_page_id = page["id"]
            except NotionServiceError:
                logger.warning("Source %s could not sync to Notion.", source.id)

    async def _sync_source_items(self, items: list[SourceItem]) -> None:
        for item in items:
            try:
                page = await self.notion.sync_source_item(item)
                if not item.notion_page_id:
                    await asyncio.to_thread(
                        self._save_source_item_page_id,
                        item.id,
                        page["id"],
                    )
                    item.notion_page_id = page["id"]
            except NotionServiceError:
                logger.warning("Source item %s could not sync to Notion.", item.id)

    async def _sync_report(self, report: Report) -> None:
        try:
            page = await self.notion.sync_report(report)
            if not report.notion_page_id:
                await asyncio.to_thread(
                    self._save_report_page_id,
                    report.id,
                    page["id"],
                )
                report.notion_page_id = page["id"]
        except NotionServiceError:
            logger.warning("Monitoring report %s could not sync to Notion.", report.id)

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

    @staticmethod
    def _save_report_page_id(report_id: int, page_id: str) -> None:
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report:
                report.notion_page_id = page_id
