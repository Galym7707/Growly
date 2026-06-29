from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.database import session_scope
from app.models import Publication, Report
from app.repositories.reports_repo import ReportsRepository
from app.services.ai_service import AIService
from app.services.notion_service import NotionService
from app.utils.errors import AIServiceError, ConfigurationError, NotionServiceError

logger = logging.getLogger(__name__)

_REPORT_CHAT_FALLBACK_PREFIX = {
    "ru": "Краткий вывод отчёта:",
    "en": "Report summary:",
    "kk": "Есеп қорытындысы:",
}
_REPORT_CHAT_FALLBACK_EMPTY = {
    "ru": "Не удалось получить ответ ИИ. Откройте отчёт, чтобы посмотреть детали.",
    "en": "Could not get an AI answer. Open the report to review the details.",
    "kk": "ИИ жауабын алу мүмкін болмады. Толығырақ есепті ашыңыз.",
}
_REPORT_IDEAS_HEADER = {
    "ru": "Идеи постов из отчёта:",
    "en": "Post ideas from the report:",
    "kk": "Есептен жазба идеялары:",
}
_REPORT_IDEAS_EMPTY = {
    "ru": (
        "В отчёте пока нет готовых идей постов. Создайте контент-план, "
        "чтобы сгенерировать темы."
    ),
    "en": (
        "The report has no ready post ideas yet. Create a content plan to "
        "generate topics."
    ),
    "kk": (
        "Есепте әзірге дайын жазба идеялары жоқ. Тақырып жасау үшін "
        "контент-жоспар құрыңыз."
    ),
}


class ReportService:
    def __init__(
        self,
        ai: AIService | None = None,
        notion: NotionService | None = None,
        groq: AIService | None = None,
    ) -> None:
        self.ai = ai or groq or AIService()
        self.notion = notion or NotionService()

    async def list_latest(self, limit: int = 10) -> list[Report]:
        def load() -> list[Report]:
            with session_scope() as session:
                return ReportsRepository(session).list_latest(limit)

        return await asyncio.to_thread(load)

    async def list_latest_summary(self, limit: int = 10) -> list[Report]:
        def load() -> list[Report]:
            with session_scope() as session:
                return ReportsRepository(session).list_latest_summary(limit)

        return await asyncio.to_thread(load)

    async def get_report(self, report_id: int) -> Report | None:
        def load() -> Report | None:
            with session_scope() as session:
                return ReportsRepository(session).get_report(report_id)

        return await asyncio.to_thread(load)

    async def latest_report(self, report_type: str) -> Report | None:
        def load() -> Report | None:
            with session_scope() as session:
                return ReportsRepository(session).latest_report(report_type)

        return await asyncio.to_thread(load)

    async def latest_report_summary(self, report_type: str) -> Report | None:
        def load() -> Report | None:
            with session_scope() as session:
                return ReportsRepository(session).latest_report_summary(report_type)

        return await asyncio.to_thread(load)

    async def answer_question(
        self,
        report_id: int,
        message: str,
        language: str = "ru",
    ) -> str:
        report = await self.get_report(report_id)
        if report is None:
            raise ValueError("Отчёт не найден.")
        context = self._report_chat_context(report, message, language)
        try:
            answer = await self.ai.answer_report_question(context)
            if answer and answer.strip():
                return answer.strip()
        except (AIServiceError, ConfigurationError):
            logger.warning(
                "Report chat AI unavailable for report %s; using fallback.",
                report_id,
            )
        return self._fallback_answer(report, language)

    async def report_ideas(self, report_id: int, language: str = "ru") -> str:
        report = await self.get_report(report_id)
        if report is None:
            raise ValueError("Отчёт не найден.")
        raw = report.raw_json if isinstance(report.raw_json, dict) else {}
        ideas: list[str] = []
        for key in ("content_ideas", "dominant_topics", "content_gaps"):
            ideas = [
                str(value).strip()
                for value in (raw.get(key) or [])
                if str(value).strip()
            ]
            if ideas:
                break
        lang = language if language in self._REPORT_LANGS else "ru"
        if not ideas:
            return _REPORT_IDEAS_EMPTY[lang]
        body = "\n".join(f"• {idea}" for idea in ideas[:10])
        return f"{_REPORT_IDEAS_HEADER[lang]}\n{body}"

    _REPORT_LANGS = ("ru", "en", "kk")

    @staticmethod
    def _report_chat_context(
        report: Report,
        message: str,
        language: str,
    ) -> dict[str, Any]:
        raw = report.raw_json if isinstance(report.raw_json, dict) else {}
        market_context = (
            raw.get("market_context")
            if isinstance(raw.get("market_context"), dict)
            else {}
        )

        def field(*names: str) -> list[Any]:
            for name in names:
                value = raw.get(name)
                if isinstance(value, list) and value:
                    return value[:10]
            return []

        return {
            "language": language,
            "question": message,
            "report_title": report.title,
            "report_type": report.report_type,
            "topic": market_context.get("topic")
            or report.query
            or report.title,
            "region": market_context.get("region"),
            "summary": str(report.summary or "")[:1500],
            "audience_pains": field("audience_pains"),
            "repeated_offers": field("repeated_offers", "repeating_offers"),
            "repeated_ctas": field("repeated_ctas", "repeating_ctas"),
            "content_gaps": field("content_gaps"),
            "content_ideas": field("content_ideas"),
            "weekly_priorities": field("weekly_priorities", "actions_this_week"),
        }

    @staticmethod
    def _fallback_answer(report: Report, language: str) -> str:
        lang = language if language in ("ru", "en", "kk") else "ru"
        summary = str(report.summary or "").strip()
        if summary:
            return f"{_REPORT_CHAT_FALLBACK_PREFIX[lang]} {summary}"
        return _REPORT_CHAT_FALLBACK_EMPTY[lang]

    async def sync_report_to_notion(self, report_id: int) -> str:
        report = await self.get_report(report_id)
        if report is None:
            raise ValueError("Отчёт не найден.")
        page = await asyncio.wait_for(
            self.notion.sync_report(report),
            timeout=30,
        )
        page_id = str(page["id"])
        await asyncio.to_thread(self._save_page_id, report.id, page_id)
        return self.notion.page_url(page_id)

    async def generate_weekly_performance_report(self) -> Report | None:
        week_start, week_end = self._previous_week()
        start_dt = datetime.combine(week_start, time.min, tzinfo=UTC)
        end_dt = datetime.combine(week_end + timedelta(days=1), time.min, tzinfo=UTC)
        context = await asyncio.to_thread(self._performance_context, start_dt, end_dt)
        if not self._has_useful_performance_data(context):
            return None
        context["language"] = "ru"
        text = await self.ai.generate_weekly_performance_report(context)

        def save() -> Report:
            with session_scope() as session:
                return ReportsRepository(session).create_report(
                    report_type="performance",
                    title=f"Отчёт по публикациям: {week_start.isoformat()}",
                    report_text=text,
                    week_start=week_start,
                    week_end=week_end,
                    summary=(
                        f"Черновиков: {context['counts']['drafts']}; "
                        f"опубликовано: {context['counts']['published']}."
                    ),
                )

        report = await asyncio.to_thread(save)
        try:
            page = await self.notion.sync_report(report)
            await asyncio.to_thread(self._save_page_id, report.id, page["id"])
            report.notion_page_id = page["id"]
        except NotionServiceError:
            logger.warning("Performance report %s could not sync to Notion.", report.id)
        return report

    @staticmethod
    def _has_useful_performance_data(context: dict[str, Any]) -> bool:
        counts = context.get("counts") or {}
        if int(counts.get("published") or 0) == 0:
            return False
        metric_fields = ("views", "reactions", "comments", "clicks", "leads")
        return any(
            any(row.get(field) is not None for field in metric_fields)
            for row in context.get("publication_metrics", [])
            if isinstance(row, dict)
        )

    async def list_recent_publications(self, limit: int = 20) -> list[Publication]:
        def load() -> list[Publication]:
            with session_scope() as session:
                return ReportsRepository(session).list_recent_publications(limit)

        return await asyncio.to_thread(load)

    async def update_publication_metrics(
        self,
        publication_id: int,
        *,
        views: int,
        reactions: int,
        comments: int,
        clicks: int,
        leads: int,
        notes: str | None,
    ) -> Publication:
        values = (views, reactions, comments, clicks, leads)
        if any(value < 0 for value in values):
            raise ValueError("Метрики публикации не могут быть отрицательными.")

        def update() -> Publication:
            with session_scope() as session:
                repo = ReportsRepository(session)
                publication = repo.get_publication(publication_id)
                if publication is None:
                    raise ValueError("Публикация не найдена.")
                return repo.update_publication_metrics(
                    publication,
                    views=views,
                    reactions=reactions,
                    comments=comments,
                    clicks=clicks,
                    leads=leads,
                    notes=notes,
                )

        publication = await asyncio.to_thread(update)
        try:
            await self.notion.sync_publication(publication)
        except NotionServiceError:
            logger.warning("Publication %s metrics could not sync to Notion.", publication.id)
        return publication

    @staticmethod
    def _previous_week() -> tuple[date, date]:
        today = datetime.now(UTC).date()
        current_start = today - timedelta(days=today.weekday())
        previous_start = current_start - timedelta(days=7)
        return previous_start, previous_start + timedelta(days=6)

    @staticmethod
    def _performance_context(start: datetime, end: datetime) -> dict[str, Any]:
        with session_scope() as session:
            repo = ReportsRepository(session)
            publications = repo.list_publications_for_period(start, end)
            return {
                "period": {"start": start.date(), "end": (end - timedelta(days=1)).date()},
                "counts": repo.performance_counts(start, end),
                "publication_metrics": [
                    {
                        "id": row.id,
                        "channel": row.channel,
                        "status": row.status,
                        "views": row.views,
                        "reactions": row.reactions,
                        "comments": row.comments_count,
                        "clicks": row.clicks,
                        "leads": row.leads,
                        "notes": row.notes,
                    }
                    for row in publications
                ],
            }

    @staticmethod
    def _save_page_id(report_id: int, page_id: str) -> None:
        with session_scope() as session:
            report = session.get(Report, report_id)
            if report:
                report.notion_page_id = page_id
