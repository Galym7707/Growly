from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import desc, select

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import MarketScanJob, Report, Setting, SourceItem
from app.repositories.market_scan_jobs_repo import MarketScanJobsRepository
from app.repositories.reports_repo import ReportsRepository
from app.repositories.sources_repo import SourcesRepository
from app.search.base import BaseSearchProvider, SearchResult
from app.search.factory import get_search_provider
from app.services.ai_service import AIService
from app.services.notion_service import NotionService
from app.utils.errors import (
    AIServiceError,
    ConfigurationError,
    NotionServiceError,
    SearchServiceError,
)
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)

MARKET_ANALYSIS_BATCH_SIZE = 8
MARKET_SCAN_PENDING_STATUS = "search_saved_analysis_pending"
TAVILY_QUERY_TIMEOUT_SECONDS = 30.0
GROQ_GENERATION_TIMEOUT_SECONDS = 60.0
NOTION_OPERATION_TIMEOUT_SECONDS = 30.0
NOTION_SYNC_TOTAL_TIMEOUT_SECONDS = 90.0
NOTION_SYNC_CONCURRENCY = 3
ProgressCallback = Callable[[str], Awaitable[None]]


class MarketIntelligenceService:
    def __init__(
        self,
        settings: Settings | None = None,
        search_provider: BaseSearchProvider | None = None,
        ai: AIService | None = None,
        notion: NotionService | None = None,
        groq: AIService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.search_provider = search_provider
        self.ai = ai or groq or AIService(self.settings)
        self.notion = notion or NotionService(self.settings)

    def _provider(self) -> BaseSearchProvider:
        if self.search_provider is None:
            self.search_provider = get_search_provider(self.settings)
        return self.search_provider

    async def create_market_scan_job(
        self,
        user_id: int | None,
        query: str,
    ) -> MarketScanJob:
        return await asyncio.to_thread(
            self._create_market_scan_job,
            user_id,
            query,
        )

    async def latest_market_scan_job(
        self,
        user_id: int,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._latest_market_scan_job, user_id)

    async def market_scan_job_id_for_report(
        self,
        report_id: int,
    ) -> int | None:
        return await asyncio.to_thread(self._job_id_for_report, report_id)

    async def cancel_market_scan_job(
        self,
        job_id: int | None,
    ) -> None:
        if job_id is None:
            return
        await self._update_job(
            job_id,
            status="cancelled",
            current_step="Отменено пользователем.",
            error_message="Task cancelled by user.",
        )

    async def fail_market_scan_job(
        self,
        job_id: int | None,
        error_message: str,
    ) -> None:
        if job_id is None:
            return
        await self._update_job(
            job_id,
            status="failed",
            current_step="Задача завершилась с ошибкой.",
            error_message=error_message,
        )

    async def web_search(
        self,
        query: str,
        *,
        max_results: int | None = None,
        include_raw_content: bool = False,
    ) -> list[SourceItem]:
        results = await asyncio.to_thread(
            self._provider().search,
            query,
            max_results,
            include_raw_content=include_raw_content,
        )
        saved = await asyncio.to_thread(self._save_results, results)
        await self._sync_source_items(saved)
        return saved

    async def run_market_scan(
        self,
        *,
        niche: str,
        region_language: str,
        competitor_keywords: str,
        user_id: int | None = None,
        job_id: int | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[Report, list[SourceItem]]:
        logger.info("market_scan_started")
        if job_id is None and user_id is not None:
            job = await self.create_market_scan_job(user_id, niche)
            job_id = job.id
        await self._set_job_step(
            job_id,
            "Шаг 1/5: ищу источники через Tavily...",
        )
        await self._emit_progress(
            progress,
            "Шаг 1/5: ищу источники через Tavily...",
        )
        queries = self.build_market_queries(
            niche=niche,
            region_language=region_language,
            competitor_keywords=competitor_keywords,
        )
        all_results: list[SearchResult] = []
        search_errors: list[str] = []
        for query in queries:
            logger.info("tavily_query_started query=%s", query)
            try:
                rows = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._provider().search,
                        query,
                        self.settings.search_max_results,
                        include_raw_content=False,
                    ),
                    timeout=TAVILY_QUERY_TIMEOUT_SECONDS,
                )
                logger.info(
                    "tavily_query_finished query=%s results_count=%d status=ready",
                    query,
                    len(rows),
                )
            except TimeoutError:
                rows = []
                search_errors.append(f"Tavily timeout: {query}")
                logger.warning(
                    "tavily_query_finished query=%s results_count=0 status=timeout",
                    query,
                )
            except SearchServiceError as exc:
                rows = []
                search_errors.append(str(exc))
                logger.warning(
                    "tavily_query_finished query=%s results_count=0 status=failed",
                    query,
                )
            all_results.extend(rows)
        unique_results = self._deduplicate_results(all_results)
        logger.info("tavily_results_count=%d", len(unique_results))
        if not unique_results and search_errors:
            await self.fail_market_scan_job(job_id, search_errors[-1])
            raise SearchServiceError(
                "Tavily search did not return results before the timeout."
            )

        step_two = f"Шаг 2/5: найдено {len(unique_results)} результатов."
        await self._set_job_step(job_id, step_two)
        await self._emit_progress(progress, step_two)
        await self._set_job_step(
            job_id,
            "Шаг 3/5: сохраняю источники в Supabase...",
        )
        await self._emit_progress(
            progress,
            "Шаг 3/5: сохраняю источники в Supabase...",
        )
        saved = await asyncio.to_thread(self._save_results, unique_results)
        logger.info("source_items_saved_count=%d", len(saved))
        await self._update_job(
            job_id,
            sources_count=len(saved),
            error_message="; ".join(search_errors) if search_errors else None,
        )
        await self._emit_progress(
            progress,
            (
                f"Источники сохранены: {len(saved)}. Даже если AI-анализ не "
                "завершится, данные уже не потеряются."
            ),
        )

        await self._set_job_step(
            job_id,
            "Шаг 4/5: анализирую источники через AI...",
        )
        await self._emit_progress(
            progress,
            "Шаг 4/5: анализирую источники через AI...",
        )
        logger.info("groq_analysis_started")
        try:
            report, saved = await self._complete_market_scan_analysis(
                niche=niche,
                queries=queries,
                saved=saved,
                job_id=job_id,
                progress=progress,
            )
            logger.info("groq_status=ready")
            logger.info("groq_analysis_finished")
        except (AIServiceError, TimeoutError) as exc:
            if isinstance(exc, TimeoutError):
                groq_status = "timeout"
            else:
                groq_status = (
                    "rate_limited" if exc.is_rate_limited else "unavailable"
                )
            logger.warning("groq_status=%s", groq_status)
            logger.warning(
                "groq_analysis_failed status=%s error_type=%s",
                groq_status,
                type(exc).__name__,
            )
            report = await asyncio.to_thread(
                self._save_partial_market_scan_report,
                niche,
                queries,
                saved,
                groq_status,
            )
        await self._update_job(
            job_id,
            status=(
                "completed"
                if report.status == "ready"
                else "analysis_pending"
            ),
            report_id=report.id,
            error_message=(
                None
                if report.status == "ready"
                else "AI analysis did not complete."
            ),
        )

        await self._set_job_step(
            job_id,
            "Шаг 5/5: сохраняю отчет в Notion...",
        )
        await self._emit_progress(
            progress,
            "Шаг 5/5: сохраняю отчет в Notion...",
        )
        logger.info("notion_sync_started")
        source_sync_failures = await self._sync_source_items(saved)
        report_synced = await self._sync_report(report)
        logger.info("notion_sync_finished")
        final_errors: list[str] = []
        if report.status != "ready":
            final_errors.append("AI analysis did not complete.")
        if source_sync_failures:
            final_errors.append(
                f"Notion source sync incomplete: {source_sync_failures} items."
            )
        if not report_synced:
            final_errors.append("Notion report sync incomplete.")
        await self._set_job_step(
            job_id,
            "Готово.",
            status=(
                "completed"
                if report.status == "ready"
                else "analysis_pending"
            ),
            error_message=" ".join(final_errors) if final_errors else None,
        )
        await self._emit_progress(progress, "Готово.")
        logger.info("report_status=%s", report.status)
        return report, saved

    async def retry_latest_analysis(
        self,
        report_id: int | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[Report, list[SourceItem]]:
        report, saved = await asyncio.to_thread(
            self._load_pending_scan,
            report_id,
        )
        if report is None:
            raise ValueError("No market scan is waiting for AI analysis.")
        if not saved:
            raise ValueError("The pending market scan has no saved source items.")

        metadata = report.raw_json or {}
        queries = [
            str(query)
            for query in metadata.get("queries", [])
            if str(query).strip()
        ]
        if not queries:
            queries = [report.query or "latest saved market sources"]
        job_id = await asyncio.to_thread(self._job_id_for_report, report.id)
        await self._set_job_step(
            job_id,
            "Шаг 4/5: анализирую источники через AI...",
            status="running",
        )
        await self._emit_progress(
            progress,
            "Шаг 4/5: анализирую источники через AI...",
        )
        logger.info("groq_analysis_started")

        try:
            completed, saved = await self._complete_market_scan_analysis(
                niche=report.query or "latest market scan",
                queries=queries,
                saved=saved,
                existing_report_id=report.id,
                job_id=job_id,
                progress=progress,
            )
            logger.info("groq_status=ready")
            logger.info("groq_analysis_finished")
            await self._set_job_step(
                job_id,
                "Шаг 5/5: сохраняю отчет в Notion...",
            )
            await self._emit_progress(
                progress,
                "Шаг 5/5: сохраняю отчет в Notion...",
            )
            logger.info("notion_sync_started")
            source_sync_failures = await self._sync_source_items(saved)
            report_synced = await self._sync_report(completed)
            logger.info("notion_sync_finished")
            final_error = None
            if source_sync_failures or not report_synced:
                final_error = (
                    "Notion sync incomplete: "
                    f"source_items_failed={source_sync_failures}, "
                    f"report_synced={report_synced}."
                )
            await self._set_job_step(
                job_id,
                "Готово.",
                status="completed",
                report_id=completed.id,
                error_message=final_error,
                clear_error=final_error is None,
            )
            await self._emit_progress(progress, "Готово.")
            logger.info("report_status=%s", completed.status)
            return completed, saved
        except (AIServiceError, TimeoutError) as exc:
            if isinstance(exc, TimeoutError):
                groq_status = "timeout"
            else:
                groq_status = (
                    "rate_limited" if exc.is_rate_limited else "unavailable"
                )
            logger.warning("groq_status=%s", groq_status)
            logger.warning(
                "groq_analysis_failed status=%s error_type=%s",
                groq_status,
                type(exc).__name__,
            )
            pending = await asyncio.to_thread(
                self._record_pending_retry_failure,
                report.id,
                groq_status,
            )
            logger.info("notion_sync_started")
            await self._sync_report(pending)
            logger.info("notion_sync_finished")
            await self._set_job_step(
                job_id,
                "AI-анализ ожидает повторного запуска.",
                status="analysis_pending",
                report_id=pending.id,
                error_message="AI analysis did not complete.",
            )
            logger.info("report_status=%s", pending.status)
            return pending, saved

    async def source_items_for_report(self, report_id: int) -> list[SourceItem]:
        return await asyncio.to_thread(self._load_report_source_items, report_id)

    async def _complete_market_scan_analysis(
        self,
        *,
        niche: str,
        queries: list[str],
        saved: list[SourceItem],
        existing_report_id: int | None = None,
        job_id: int | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[Report, list[SourceItem]]:
        analysis, batch_summaries = await self._analyze_source_item_batches(
            " | ".join(queries),
            saved,
            job_id=job_id,
            progress=progress,
        )
        saved = await asyncio.to_thread(
            self._apply_source_analysis,
            [item.id for item in saved],
            analysis,
        )

        report_payload = await self.generate_market_scan_report(
            niche,
            [self.source_item_to_dict(item) for item in saved],
            batch_summaries=batch_summaries,
        )
        if existing_report_id is None:
            report = await asyncio.to_thread(
                self._save_market_scan_report,
                niche,
                report_payload,
                saved,
                queries,
            )
        else:
            report = await asyncio.to_thread(
                self._update_market_scan_report,
                existing_report_id,
                report_payload,
                saved,
                queries,
            )
        return report, saved

    async def _analyze_source_item_batches(
        self,
        query: str,
        saved: list[SourceItem],
        *,
        job_id: int | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        analyses: list[dict[str, Any]] = []
        known_urls = {item.url for item in saved if item.url}
        batch_count = max(
            1,
            (len(saved) + MARKET_ANALYSIS_BATCH_SIZE - 1)
            // MARKET_ANALYSIS_BATCH_SIZE,
        )
        for batch_number, start in enumerate(
            range(0, len(saved), MARKET_ANALYSIS_BATCH_SIZE),
            start=1,
        ):
            batch = saved[start : start + MARKET_ANALYSIS_BATCH_SIZE]
            batch_step = (
                f"Шаг 4/5: AI-пакет {batch_number}/{batch_count}, "
                f"источников {len(batch)}..."
            )
            await self._set_job_step(job_id, batch_step)
            await self._emit_progress(progress, batch_step)
            response = await asyncio.wait_for(
                self.ai.analyze_market_search(
                    {
                        "query": query,
                        "batch_number": batch_number,
                        "source_items": [
                            self._compact_source_item(item) for item in batch
                        ],
                        "limitations": (
                            "These are saved public web search results only. No private "
                            "social-media or platform analytics are available."
                        ),
                    }
                ),
                timeout=GROQ_GENERATION_TIMEOUT_SECONDS,
            )
            payload = self._parse_dict(response, "Market search analysis")
            payload["source_items"] = [
                row
                for row in payload.get("source_items", [])
                if isinstance(row, dict) and row.get("url") in known_urls
            ]
            analyses.append(payload)
        synthesis_step = "Шаг 4/5: объединяю результаты AI-анализа..."
        await self._set_job_step(job_id, synthesis_step)
        await self._emit_progress(progress, synthesis_step)
        return self._merge_batch_analyses(analyses), [
            self._batch_summary(payload) for payload in analyses
        ]

    async def analyze_search_results(
        self,
        query: str,
        results: list[SearchResult],
    ) -> dict[str, Any]:
        response = await asyncio.wait_for(
            self.ai.analyze_market_search(
                {
                    "query": query,
                    "results": [asdict(result) for result in results],
                    "limitations": (
                        "These are public web search results only. No private social-media "
                        "or platform analytics are available."
                    ),
                }
            ),
            timeout=GROQ_GENERATION_TIMEOUT_SECONDS,
        )
        return self._parse_dict(response, "Market search analysis")

    async def generate_market_scan_report(
        self,
        query: str,
        saved_source_items: list[dict[str, Any]],
        *,
        batch_summaries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        aggregate_summary = self._batch_summary(
            self._merge_batch_analyses(batch_summaries or [])
        )
        response = await asyncio.wait_for(
            self.ai.generate_market_scan(
                {
                    "query": query,
                    "saved_source_item_batch_summary": aggregate_summary,
                    "source_evidence": [
                        {
                            "id": item.get("id"),
                            "title": str(item.get("title") or "")[:160],
                            "url": str(item.get("url") or "")[:500],
                        }
                        for item in saved_source_items
                    ],
                    "sources_count": len(saved_source_items),
                    "generated_at": datetime.now(UTC).isoformat(),
                }
            ),
            timeout=GROQ_GENERATION_TIMEOUT_SECONDS,
        )
        payload = self._parse_dict(response, "Market scan")
        payload["sources_checked"] = len(saved_source_items)
        return payload

    async def generate_competitor_report(
        self,
        *,
        query: str | None = None,
    ) -> Report:
        context = await asyncio.to_thread(self._competitor_context, query)
        if not context["source_items"]:
            raise ValueError(
                "Нет сохранённых Source Items. Сначала выполните /market_scan."
            )
        response = await asyncio.wait_for(
            self.ai.generate_competitor_report(context),
            timeout=GROQ_GENERATION_TIMEOUT_SECONDS,
        )
        payload = self._parse_dict(response, "Competitor report")
        allowed_urls = [
            str(row["url"])
            for row in context["source_items"]
            if row.get("url")
        ]
        payload = self._normalize_competitor_report(payload, allowed_urls)
        text = self.render_competitor_report(payload)
        evidence = payload["source_urls"]
        summary = str(payload.get("executive_summary") or "Нет подтверждённого вывода.")[
            :1800
        ]
        report = await asyncio.to_thread(
            self._save_competitor_report,
            query,
            text,
            summary,
            evidence,
            context,
            payload,
        )
        await self._sync_report(report)
        return report

    async def has_source_items(self) -> bool:
        def check() -> bool:
            with session_scope() as session:
                return bool(
                    session.scalar(select(SourceItem.id).limit(1))
                )

        return await asyncio.to_thread(check)

    @staticmethod
    def build_market_queries(
        *,
        niche: str,
        region_language: str,
        competitor_keywords: str,
    ) -> list[str]:
        clean_niche = niche.strip()
        clean_region = region_language.strip()
        clean_competitors = competitor_keywords.strip()
        queries = [
            f"{clean_niche} competitors {clean_region}",
            f"{clean_niche} market trends {clean_region}",
            f"{clean_niche} customer problems {clean_region}",
            f"{clean_niche} Telegram Instagram marketing examples {clean_region}",
        ]
        if clean_competitors and clean_competitors.lower() not in {
            "нет",
            "none",
            "-",
        }:
            queries.append(f"{clean_competitors} content marketing {clean_region}")
        return queries

    @staticmethod
    def source_item_to_dict(item: SourceItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "query": item.query,
            "title": item.title,
            "url": item.url,
            "snippet": item.snippet,
            "content": item.content,
            "published_at": item.published_at,
            "score": float(item.score) if item.score is not None else None,
            "ai_summary": item.ai_summary,
            "topics": item.topics_json,
            "offers": item.offers_json,
            "ctas": item.ctas_json,
            "pains": item.pains_json,
            "objections": item.objections_json,
            "content_gaps": item.content_gaps_json,
            "ideas": item.ideas_json,
        }

    @classmethod
    def _compact_source_item(cls, item: SourceItem) -> dict[str, Any]:
        payload = cls.source_item_to_dict(item)
        return {
            "id": payload["id"],
            "title": str(payload.get("title") or "")[:240],
            "url": payload.get("url"),
            "snippet": str(payload.get("snippet") or "")[:800],
            "published_at": payload.get("published_at"),
            "score": payload.get("score"),
        }

    @classmethod
    def _merge_batch_analyses(
        cls,
        analyses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        list_fields = (
            "dominant_topics",
            "repeated_offers",
            "repeated_ctas",
            "audience_pains",
            "objections",
            "formats",
            "content_gaps",
            "risks",
            "content_ideas",
            "weekly_priorities",
            "evidence_urls",
        )
        merged: dict[str, Any] = {
            field: cls._deduplicate_values(
                item
                for analysis in analyses
                for item in cls._list(analysis.get(field))
            )
            for field in list_fields
        }
        merged["source_items"] = [
            item
            for analysis in analyses
            for item in cls._list(analysis.get("source_items"))
            if isinstance(item, dict)
        ]
        return merged

    @classmethod
    def _batch_summary(cls, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: [
                str(value)[:300]
                for value in cls._list(payload.get(key))[:12]
            ]
            for key in (
                "dominant_topics",
                "repeated_offers",
                "repeated_ctas",
                "audience_pains",
                "objections",
                "formats",
                "content_gaps",
                "risks",
                "content_ideas",
                "weekly_priorities",
                "evidence_urls",
            )
        }

    @staticmethod
    def _deduplicate_values(values: Any) -> list[Any]:
        unique: list[Any] = []
        seen: set[str] = set()
        for value in values:
            marker = str(value)
            if marker not in seen:
                seen.add(marker)
                unique.append(value)
        return unique

    @staticmethod
    def render_market_scan_report(payload: dict[str, Any]) -> str:
        def section(title: str, value: Any) -> str:
            if isinstance(value, list):
                body = "\n".join(f"- {item}" for item in value) or "- Нет данных"
            else:
                body = str(value or "Нет данных")
            return f"{title}\n{body}"

        return "\n\n".join(
            [
                section("Краткий вывод", payload.get("executive_summary")),
                section("Доминирующие темы", payload.get("dominant_topics")),
                section("Повторяющиеся офферы", payload.get("repeated_offers")),
                section("Повторяющиеся CTA", payload.get("repeated_ctas")),
                section("Боли аудитории", payload.get("audience_pains")),
                section("Возражения", payload.get("objections")),
                section("Контентные пробелы", payload.get("content_gaps")),
                section("Идеи контента", payload.get("content_ideas")),
                section("Приоритеты недели", payload.get("weekly_priorities")),
                section(
                    "Риски и ограничения",
                    payload.get("risks_and_limitations"),
                ),
                section("Источники", payload.get("evidence_urls")),
            ]
        )

    @staticmethod
    def render_competitor_report(payload: dict[str, Any]) -> str:
        def clean_cell(value: Any) -> str:
            return str(value or "Не подтверждено").replace("|", "/").replace("\n", " ")

        def bullets(values: Any, *, empty: str = "Нет подтверждённых данных") -> str:
            rows = values if isinstance(values, list) else []
            return "\n".join(f"- {clean_cell(row)}" for row in rows) or f"- {empty}"

        table = [
            "| Competitor | Channel | Offer | Price/value | Content style | CTA | "
            "Strengths | Weaknesses | Opportunity |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        evidence_by_competitor: list[str] = []
        for row in payload.get("competitors", []):
            table.append(
                "| "
                + " | ".join(
                    clean_cell(row.get(field))
                    for field in (
                        "competitor",
                        "channel",
                        "offer",
                        "price_value",
                        "content_style",
                        "cta",
                        "strengths",
                        "weaknesses",
                        "opportunity",
                    )
                )
                + " |"
            )
            evidence_by_competitor.append(
                f"- {clean_cell(row.get('competitor'))}: "
                + ", ".join(row.get("source_urls") or [])
            )
        if len(table) == 2:
            table.append(
                "| Не идентифицированы | Не подтверждено | Не подтверждено | "
                "Не подтверждено | Не подтверждено | Не подтверждено | "
                "Не подтверждено | Не подтверждено | Требуется больше данных |"
            )

        return "\n\n".join(
            [
                "Executive summary\n"
                + clean_cell(payload.get("executive_summary") or "Нет подтверждённого вывода"),
                "Competitor table\n" + "\n".join(table),
                "Repeating offers\n" + bullets(payload.get("repeating_offers")),
                "Repeating CTAs\n" + bullets(payload.get("repeating_ctas")),
                "Content gaps\n" + bullets(payload.get("content_gaps")),
                "Recommended positioning\n"
                + bullets(payload.get("recommended_positioning")),
                "5 actions for this week\n"
                + bullets(payload.get("actions_this_week")),
                "Source URLs\n" + bullets(payload.get("source_urls")),
                "Evidence by competitor\n"
                + (
                    "\n".join(evidence_by_competitor)
                    or "- Нет конкурентов с подтверждёнными URL"
                ),
                "Limitations\n" + bullets(payload.get("limitations")),
            ]
        )

    @classmethod
    def _normalize_competitor_report(
        cls,
        payload: dict[str, Any],
        allowed_urls: list[str],
    ) -> dict[str, Any]:
        allowed = set(allowed_urls)

        def strings(value: Any, limit: int) -> list[str]:
            if not isinstance(value, list):
                return []
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ][:limit]

        competitors: list[dict[str, Any]] = []
        for value in cls._list(payload.get("competitors")):
            if not isinstance(value, dict):
                continue
            urls = [
                url
                for url in strings(value.get("source_urls"), 10)
                if url in allowed
            ]
            if not urls:
                continue
            competitors.append(
                {
                    field: str(value.get(field) or "Не подтверждено").strip()
                    for field in (
                        "competitor",
                        "channel",
                        "offer",
                        "price_value",
                        "content_style",
                        "cta",
                        "strengths",
                        "weaknesses",
                        "opportunity",
                    )
                }
                | {"source_urls": urls}
            )

        requested_urls = [
            url
            for url in strings(payload.get("source_urls"), 50)
            if url in allowed
        ]
        competitor_urls = [
            url
            for row in competitors
            for url in row["source_urls"]
        ]
        source_urls = cls._deduplicate_values(requested_urls + competitor_urls)
        if not source_urls:
            source_urls = allowed_urls[:50]

        return {
            "executive_summary": str(
                payload.get("executive_summary")
                or "Недостаточно данных для подтверждённого конкурентного вывода."
            ).strip(),
            "competitors": competitors[:30],
            "repeating_offers": strings(payload.get("repeating_offers"), 12),
            "repeating_ctas": strings(payload.get("repeating_ctas"), 12),
            "content_gaps": strings(payload.get("content_gaps"), 12),
            "recommended_positioning": strings(
                payload.get("recommended_positioning"), 10
            ),
            "actions_this_week": strings(payload.get("actions_this_week"), 5),
            "source_urls": source_urls,
            "limitations": strings(payload.get("limitations"), 10),
        }

    @staticmethod
    def _parse_dict(response: str, label: str) -> dict[str, Any]:
        payload = parse_json_response(response)
        if not isinstance(payload, dict):
            raise AIServiceError(f"{label} response was not a JSON object.")
        return payload

    @staticmethod
    def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
        unique: dict[str, SearchResult] = {}
        for result in results:
            unique.setdefault(result.url, result)
        return list(unique.values())

    @staticmethod
    def _save_results(results: list[SearchResult]) -> list[SourceItem]:
        with session_scope() as session:
            repo = SourcesRepository(session)
            return [repo.create_search_item(result) for result in results]

    @staticmethod
    def _apply_source_analysis(
        item_ids: list[int],
        analysis: dict[str, Any],
    ) -> list[SourceItem]:
        per_url = {
            str(row.get("url") or ""): row
            for row in analysis.get("source_items", [])
            if isinstance(row, dict)
        }
        with session_scope() as session:
            repo = SourcesRepository(session)
            items = list(
                session.scalars(
                    select(SourceItem)
                    .where(SourceItem.id.in_(item_ids))
                    .order_by(SourceItem.id)
                )
            )
            for item in items:
                detail = per_url.get(item.url, {})
                if not detail:
                    detail = {
                        "ai_summary": item.snippet,
                        "topics": analysis.get("dominant_topics"),
                        "offers": analysis.get("repeated_offers"),
                        "ctas": analysis.get("repeated_ctas"),
                        "pains": analysis.get("audience_pains"),
                        "objections": analysis.get("objections"),
                        "content_gaps": analysis.get("content_gaps"),
                        "ideas": analysis.get("content_ideas"),
                    }
                repo.update_search_item_analysis(item, detail)
            return items

    async def _sync_source_items(self, items: list[SourceItem]) -> int:
        semaphore = asyncio.Semaphore(NOTION_SYNC_CONCURRENCY)

        async def sync_item(item: SourceItem) -> bool:
            async with semaphore:
                try:
                    page = await asyncio.wait_for(
                        self.notion.sync_source_item(item),
                        timeout=NOTION_OPERATION_TIMEOUT_SECONDS,
                    )
                    if not item.notion_page_id:
                        await asyncio.to_thread(
                            self._save_source_item_page_id,
                            item.id,
                            page["id"],
                        )
                        item.notion_page_id = page["id"]
                    return True
                except TimeoutError:
                    logger.warning(
                        "Source item %s Notion sync timed out.",
                        item.id,
                    )
                    return False
                except (ConfigurationError, NotionServiceError):
                    logger.warning(
                        "Source item %s could not sync to Notion.",
                        item.id,
                    )
                    return False

        try:
            outcomes = await asyncio.wait_for(
                asyncio.gather(*(sync_item(item) for item in items)),
                timeout=NOTION_SYNC_TOTAL_TIMEOUT_SECONDS,
            )
            return outcomes.count(False)
        except TimeoutError:
            logger.warning(
                "Notion source item batch sync exceeded %.0f seconds.",
                NOTION_SYNC_TOTAL_TIMEOUT_SECONDS,
            )
            return len(items)

    async def _sync_report(self, report: Report) -> bool:
        try:
            page = await asyncio.wait_for(
                self.notion.sync_report(report),
                timeout=NOTION_OPERATION_TIMEOUT_SECONDS,
            )
            if not report.notion_page_id:
                await asyncio.to_thread(
                    self._save_report_page_id, report.id, page["id"]
                )
                report.notion_page_id = page["id"]
            return True
        except TimeoutError:
            logger.warning("Report %s Notion sync timed out.", report.id)
            return False
        except (ConfigurationError, NotionServiceError):
            logger.warning("Report %s could not sync to Notion.", report.id)
            return False

    @staticmethod
    async def _emit_progress(
        progress: ProgressCallback | None,
        message: str,
    ) -> None:
        if progress is None:
            return
        try:
            await progress(message)
        except Exception:
            logger.exception(
                "Could not send market scan progress update to Telegram."
            )

    async def _set_job_step(
        self,
        job_id: int | None,
        current_step: str,
        *,
        status: str | None = None,
        report_id: int | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
    ) -> None:
        await self._update_job(
            job_id,
            status=status,
            current_step=current_step,
            report_id=report_id,
            error_message=error_message,
            clear_error=clear_error,
        )

    @staticmethod
    async def _update_job(
        job_id: int | None,
        *,
        status: str | None = None,
        current_step: str | None = None,
        sources_count: int | None = None,
        report_id: int | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
    ) -> None:
        if job_id is None:
            return

        def update() -> None:
            with session_scope() as session:
                repo = MarketScanJobsRepository(session)
                job = repo.get(job_id)
                if job is not None:
                    repo.update(
                        job,
                        status=status,
                        current_step=current_step,
                        sources_count=sources_count,
                        report_id=report_id,
                        error_message=error_message,
                        clear_error=clear_error,
                    )

        await asyncio.to_thread(update)

    @staticmethod
    def _create_market_scan_job(
        user_id: int | None,
        query: str,
    ) -> MarketScanJob:
        with session_scope() as session:
            return MarketScanJobsRepository(session).create(
                user_id=user_id,
                query=query,
            )

    @staticmethod
    def _latest_market_scan_job(user_id: int) -> dict[str, Any] | None:
        with session_scope() as session:
            job = MarketScanJobsRepository(session).latest_for_user(user_id)
            if job is None:
                return None
            report = session.get(Report, job.report_id) if job.report_id else None
            return {
                "id": job.id,
                "task_type": "market_scan",
                "status": job.status,
                "current_step": job.current_step,
                "query": job.query,
                "sources_count": job.sources_count,
                "report_id": job.report_id,
                "report_status": report.status if report else None,
                "error_message": job.error_message,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }

    @staticmethod
    def _job_id_for_report(report_id: int) -> int | None:
        with session_scope() as session:
            job = MarketScanJobsRepository(session).latest_for_report(report_id)
            return job.id if job else None

    @classmethod
    def _save_market_scan_report(
        cls,
        query: str,
        payload: dict[str, Any],
        source_items: list[SourceItem],
        queries: list[str],
    ) -> Report:
        body = cls.render_market_scan_report(payload)
        with session_scope() as session:
            return ReportsRepository(session).create_report(
                report_type="market_scan",
                title=f"Market scan: {query}",
                report_text=body,
                summary=str(payload.get("executive_summary") or "")[:1800],
                query=query,
                sources_count=len(source_items),
                evidence=cls._list(payload.get("evidence_urls")),
                recommendations=cls._list(payload.get("weekly_priorities")),
                raw_json={
                    **payload,
                    "source_item_ids": [item.id for item in source_items],
                    "queries": queries,
                    "groq_status": "ready",
                },
                status="ready",
            )

    @classmethod
    def _save_partial_market_scan_report(
        cls,
        query: str,
        queries: list[str],
        source_items: list[SourceItem],
        groq_status: str,
    ) -> Report:
        if groq_status == "rate_limited":
            message = (
                "Search results were saved, but AI analysis is delayed due to "
                "Groq rate limits."
            )
        else:
            message = (
                "Search results were saved, but AI analysis is temporarily "
                "unavailable."
            )
        with session_scope() as session:
            return ReportsRepository(session).create_report(
                report_type="market_scan",
                title=f"Market scan: {query}",
                report_text=message,
                summary=message,
                query=query,
                sources_count=len(source_items),
                evidence=[item.url for item in source_items if item.url],
                recommendations=[],
                raw_json={
                    "source_item_ids": [item.id for item in source_items],
                    "queries": queries,
                    "groq_status": groq_status,
                    "analysis_pending_since": datetime.now(UTC).isoformat(),
                },
                status=MARKET_SCAN_PENDING_STATUS,
            )

    @classmethod
    def _update_market_scan_report(
        cls,
        report_id: int,
        payload: dict[str, Any],
        source_items: list[SourceItem],
        queries: list[str],
    ) -> Report:
        body = cls.render_market_scan_report(payload)
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report is None:
                raise ValueError(f"Market scan report {report_id} was not found.")
            return ReportsRepository(session).update_report(
                report,
                report_text=body,
                summary=str(payload.get("executive_summary") or "")[:1800],
                sources_count=len(source_items),
                evidence=cls._list(payload.get("evidence_urls")),
                recommendations=cls._list(payload.get("weekly_priorities")),
                raw_json={
                    **payload,
                    "source_item_ids": [item.id for item in source_items],
                    "queries": queries,
                    "groq_status": "ready",
                    "analysis_completed_at": datetime.now(UTC).isoformat(),
                },
                status="ready",
            )

    @staticmethod
    def _load_pending_scan(
        report_id: int | None = None,
    ) -> tuple[Report | None, list[SourceItem]]:
        with session_scope() as session:
            if report_id is None:
                report = ReportsRepository(session).latest_report_with_status(
                    "market_scan",
                    MARKET_SCAN_PENDING_STATUS,
                )
            else:
                report = session.get(Report, report_id)
                if (
                    report is not None
                    and (
                        report.report_type != "market_scan"
                        or report.status != MARKET_SCAN_PENDING_STATUS
                    )
                ):
                    report = None
            if report is None:
                return None, []
            source_ids = [
                int(item_id)
                for item_id in (report.raw_json or {}).get("source_item_ids", [])
                if str(item_id).isdigit()
            ]
            if not source_ids:
                return report, []
            items = list(
                session.scalars(
                    select(SourceItem)
                    .where(SourceItem.id.in_(source_ids))
                    .order_by(SourceItem.id)
                )
            )
            return report, items

    @staticmethod
    def _load_report_source_items(report_id: int) -> list[SourceItem]:
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report is None:
                return []
            source_ids = [
                int(item_id)
                for item_id in (report.raw_json or {}).get("source_item_ids", [])
                if str(item_id).isdigit()
            ]
            if not source_ids:
                return []
            return list(
                session.scalars(
                    select(SourceItem)
                    .where(SourceItem.id.in_(source_ids))
                    .order_by(SourceItem.id)
                )
            )

    @staticmethod
    def _record_pending_retry_failure(
        report_id: int,
        groq_status: str,
    ) -> Report:
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report is None:
                raise ValueError(f"Market scan report {report_id} was not found.")
            raw_json = dict(report.raw_json or {})
            raw_json.update(
                {
                    "groq_status": groq_status,
                    "last_retry_at": datetime.now(UTC).isoformat(),
                }
            )
            report.raw_json = raw_json
            report.status = MARKET_SCAN_PENDING_STATUS
            session.flush()
            return report

    @staticmethod
    def _save_competitor_report(
        query: str | None,
        text: str,
        summary: str,
        evidence: list[str],
        context: dict[str, Any],
        payload: dict[str, Any],
    ) -> Report:
        with session_scope() as session:
            return ReportsRepository(session).create_report(
                report_type="competitor_report",
                title=f"Competitor report: {query or 'latest evidence'}",
                report_text=text,
                summary=summary,
                query=query,
                sources_count=len(context["source_items"]),
                evidence=evidence,
                recommendations=payload.get("actions_this_week", []),
                raw_json={
                    "query": query,
                    **payload,
                    "source_item_ids": [
                        row["id"] for row in context["source_items"]
                    ],
                    "latest_market_scan_used": bool(
                        context.get("latest_market_scan")
                    ),
                    "data_limited": context.get("data_limited", True),
                },
            )

    @staticmethod
    def _competitor_context(query: str | None) -> dict[str, Any]:
        with session_scope() as session:
            items = list(
                session.scalars(
                    select(SourceItem)
                    .order_by(desc(SourceItem.created_at))
                    .limit(200)
                )
            )
            reports = ReportsRepository(session)
            market_scan = reports.latest_report("market_scan")
            settings = list(
                session.scalars(
                    select(Setting)
                    .where(Setting.key.like("business_%"))
                    .order_by(Setting.key)
                )
            )
            return {
                "query": query,
                "generated_at": datetime.now(UTC).isoformat(),
                "data_limited": len(items) < 5,
                "limitations": (
                    "Only saved public source items are available. No private "
                    "social-media data or unlinked competitor claims are permitted."
                ),
                "source_items": [
                    {
                        "id": item.id,
                        "source_name": item.source_name,
                        "source_type": item.source_type,
                        "title": str(item.title or "")[:200],
                        "url": item.url,
                        "snippet": str(item.snippet or "")[:500],
                        "ai_summary": str(item.ai_summary or "")[:500],
                        "offers": item.offers_json,
                        "ctas": item.ctas_json,
                        "content_gaps": item.content_gaps_json,
                    }
                    for item in items[:60]
                ],
                "latest_market_scan": (
                    {
                        "summary": market_scan.summary,
                        "body": str(
                            market_scan.body or market_scan.report_text or ""
                        )[:2500],
                        "evidence": market_scan.evidence_json,
                    }
                    if market_scan
                    else None
                ),
                "business_profile": {row.key: row.value for row in settings},
            }

    @staticmethod
    def _list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

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


async def analyze_search_results(
    query: str,
    results: list[SearchResult],
) -> dict[str, Any]:
    return await MarketIntelligenceService().analyze_search_results(query, results)


async def generate_market_scan_report(
    query: str,
    saved_source_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return await MarketIntelligenceService().generate_market_scan_report(
        query, saved_source_items
    )
