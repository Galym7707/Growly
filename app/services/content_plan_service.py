from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, time
from typing import Any, Awaitable, Callable

from sqlalchemy import desc, select

from app.database import session_scope
from app.models import (
    ContentPlan,
    Setting,
    SourceItem,
)
from app.repositories.reports_repo import ReportsRepository
from app.services.ai_service import AIService
from app.services.notion_service import NotionService
from app.utils.errors import AIServiceError, ConfigurationError, NotionServiceError
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)

CONTENT_PLAN_BATCH_SIZE = 8
CONTENT_PLAN_MAX_DIRECT_ITEMS = 8
CONTENT_PLAN_MAX_SNIPPET_CHARS = 300
CONTENT_PLAN_MAX_EVIDENCE_URLS = 8
CONTENT_PLAN_MAX_REPORT_SUMMARY_CHARS = 1800
ContentPlanProgress = Callable[[str], Awaitable[None]]


class ContentPlanService:
    def __init__(
        self,
        groq: AIService | None = None,
        notion: NotionService | None = None,
    ) -> None:
        self.groq = groq or AIService()
        self.notion = notion or NotionService()
        self.reduced_context_used = False

    async def generate_weekly_plan(
        self,
        business_context: dict[str, Any] | str | None = None,
        *,
        progress: ContentPlanProgress | None = None,
    ) -> list[ContentPlan]:
        self.reduced_context_used = False
        await self._emit_progress(
            progress,
            "Шаг 1/4: беру последний анализ рынка...",
        )
        data = await asyncio.to_thread(self._load_context_data, business_context)

        await self._emit_progress(
            progress,
            "Шаг 2/4: сжимаю источники для ИИ...",
        )
        context = await self._build_bounded_context(data)

        await self._emit_progress(
            progress,
            "Шаг 3/4: генерирую контент-план...",
        )
        try:
            response = await self.groq.generate_content_plan(context)
        except AIServiceError as exc:
            if exc.status != 413:
                raise
            self.reduced_context_used = True
            logger.warning(
                "Content plan payload was rejected with 413; retrying with "
                "report-summary-only context."
            )
            response = await self.groq.generate_content_plan(
                self._summary_only_context(context)
            )
        payload = parse_json_response(response)
        if not isinstance(payload, list):
            raise AIServiceError("The content plan response was not a JSON array.")
        normalized = [
            self._normalize_item(item) for item in payload if isinstance(item, dict)
        ]
        self._validate_mix(normalized)

        items = await asyncio.to_thread(self._save_plan_items, normalized)
        await self._emit_progress(
            progress,
            "Шаг 4/4: сохраняю в контент-календарь Notion...",
        )
        for item in items:
            try:
                page = await self.notion.sync_content_plan(item)
                if not item.notion_page_id:
                    await asyncio.to_thread(self._save_page_id, item.id, page["id"])
                    item.notion_page_id = page["id"]
            except (ConfigurationError, NotionServiceError):
                logger.warning("Content plan item %s could not sync to Notion.", item.id)
        await self._emit_progress(progress, "Готово.")
        return items

    async def _build_bounded_context(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        source_items = data.pop("source_items")
        data["evidence_urls"] = self._deduplicate(
            self._list(data.get("evidence_urls"))
        )[:CONTENT_PLAN_MAX_EVIDENCE_URLS]
        if len(source_items) <= CONTENT_PLAN_MAX_DIRECT_ITEMS:
            data["source_items"] = [
                self._compact_source_item(item) for item in source_items
            ]
            data["source_batch_summaries"] = []
            return data

        batch_summaries: list[dict[str, Any]] = []
        for batch_number, start in enumerate(
            range(0, len(source_items), CONTENT_PLAN_BATCH_SIZE),
            start=1,
        ):
            batch = source_items[start : start + CONTENT_PLAN_BATCH_SIZE]
            response = await self.groq.summarize_content_plan_sources(
                {
                    "batch_number": batch_number,
                    "source_items": [
                        self._compact_source_item(item) for item in batch
                    ],
                }
            )
            parsed = parse_json_response(response)
            if not isinstance(parsed, dict):
                raise AIServiceError(
                    "Content plan source summary was not a JSON object."
                )
            parsed.pop("raw_json", None)
            parsed["evidence_urls"] = self._list(parsed.get("evidence_urls"))[
                :CONTENT_PLAN_MAX_EVIDENCE_URLS
            ]
            batch_summaries.append(parsed)

        await asyncio.to_thread(
            self._save_batch_summaries,
            batch_summaries,
            source_items,
        )
        data["source_items"] = []
        data["source_batch_summaries"] = batch_summaries
        return data

    @staticmethod
    def _compact_source_item(item: SourceItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "title": str(item.title or "")[:180],
            "url": str(item.url or item.external_url or "")[:500],
            "snippet": str(item.snippet or item.ai_summary or "")[
                :CONTENT_PLAN_MAX_SNIPPET_CHARS
            ],
            "topics": list(item.topics_json or [])[:5],
            "pains": list(item.pains_json or [])[:5],
            "content_gaps": list(item.content_gaps_json or [])[:5],
        }

    @staticmethod
    def _summary_only_context(context: dict[str, Any]) -> dict[str, Any]:
        return {
            "weekly_objective": context.get("weekly_objective"),
            "business": context.get("business"),
            "latest_market_scan": context.get("latest_market_scan"),
            "latest_competitor_report": context.get(
                "latest_competitor_report"
            ),
            "evidence_urls": ContentPlanService._list(
                context.get("evidence_urls")
            )[:CONTENT_PLAN_MAX_EVIDENCE_URLS],
            "evidence_limited": True,
            "context_reduced_due_to_payload_limit": True,
            "requirements": context.get("requirements"),
        }

    @staticmethod
    async def _emit_progress(
        progress: ContentPlanProgress | None,
        message: str,
    ) -> None:
        if progress is not None:
            await progress(message)

    @staticmethod
    def _validate_mix(items: list[dict[str, Any]]) -> None:
        def descriptor(item: dict[str, Any]) -> str:
            return f"{item['channel']} {item['content_type']}".lower()

        video_tokens = ("reels", "short", "video", "ролик", "видео")
        video_tokens = (*video_tokens, "ролик", "видео")
        short_videos = sum(
            1 for item in items if any(token in descriptor(item) for token in video_tokens)
        )
        posts = sum(
            1
            for item in items
            if any(
                token in descriptor(item)
                for token in ("telegram", "instagram", "post", "пост")
            )
            and not any(token in descriptor(item) for token in video_tokens)
        )
        posts = sum(
            1
            for item in items
            if any(
                token in descriptor(item)
                for token in ("telegram", "instagram", "post", "пост")
            )
            and not any(token in descriptor(item) for token in video_tokens)
        )
        whatsapp = sum(1 for item in items if "whatsapp" in descriptor(item))
        digest = sum(
            1
            for item in items
            if any(token in descriptor(item) for token in ("digest", "дайджест"))
        )
        digest = sum(
            1
            for item in items
            if any(token in descriptor(item) for token in ("digest", "дайджест"))
        )
        if (
            len(items) < 9
            or short_videos < 2
            or posts < 5
            or whatsapp < 1
            or digest < 1
        ):
            raise AIServiceError(
                "The AI response did not contain the required posts, videos, "
                "WhatsApp message, and weekly digest."
            )

    def _load_context_data(
        self, business_context: dict[str, Any] | str | None
    ) -> dict[str, Any]:
        with session_scope() as session:
            source_items = list(
                session.scalars(
                    select(SourceItem)
                    .order_by(desc(SourceItem.collected_at))
                    .limit(80)
                )
            )
            reports_repo = ReportsRepository(session)
            latest_competitor_report = (
                reports_repo.latest_report("competitor_report")
                or reports_repo.latest_report("competitor")
            )
            latest_market_scan = reports_repo.latest_report("market_scan")
            settings = list(
                session.scalars(
                    select(Setting)
                    .where(Setting.key.like("business_%"))
                    .order_by(Setting.key)
                )
            )
            profile = {row.key: row.value for row in settings}
            market_payload = (
                latest_market_scan.raw_json
                if latest_market_scan and isinstance(latest_market_scan.raw_json, dict)
                else {}
            )
            evidence_urls = self._deduplicate(
                [
                    *(
                        latest_market_scan.evidence_json
                        if latest_market_scan
                        else []
                    ),
                    *[
                        item.url or item.external_url
                        for item in source_items
                        if item.url or item.external_url
                    ],
                ]
            )[:CONTENT_PLAN_MAX_EVIDENCE_URLS]
            return {
                "weekly_objective": business_context
                or {"note": "No additional brief supplied."},
                "business": {
                    "niche": profile.get("business_niche"),
                    "region": profile.get("business_region"),
                    "language": profile.get("business_language"),
                    "offer": profile.get("business_offer"),
                    "audience": profile.get("business_audience"),
                },
                "latest_competitor_report": (
                    {
                        "summary": str(
                            latest_competitor_report.summary or ""
                        )[:CONTENT_PLAN_MAX_REPORT_SUMMARY_CHARS],
                    }
                    if latest_competitor_report
                    else None
                ),
                "latest_market_scan": (
                    {
                        "summary": str(
                            latest_market_scan.summary or ""
                        )[:CONTENT_PLAN_MAX_REPORT_SUMMARY_CHARS],
                        "top_topics": self._list(
                            market_payload.get("dominant_topics")
                        )[:8],
                        "top_pains": self._list(
                            market_payload.get("audience_pains")
                        )[:8],
                        "top_content_gaps": self._list(
                            market_payload.get("content_gaps")
                        )[:8],
                    }
                    if latest_market_scan
                    else None
                ),
                "evidence_limited": not bool(
                    source_items or latest_competitor_report or latest_market_scan
                ),
                "evidence_urls": evidence_urls,
                "source_items": source_items,
                "requirements": {
                    "minimum_post_ideas": 5,
                    "short_video_ideas": "2-3",
                    "whatsapp_messages": 1,
                    "weekly_digest": 1,
                },
            }

    @staticmethod
    def _save_batch_summaries(
        batch_summaries: list[dict[str, Any]],
        source_items: list[SourceItem],
    ) -> None:
        with session_scope() as session:
            ReportsRepository(session).create_report(
                report_type="content_plan_source_summary",
                title="Content plan source batch summaries",
                report_text=json.dumps(
                    batch_summaries,
                    ensure_ascii=False,
                    default=str,
                ),
                summary=f"Summarized {len(source_items)} source items.",
                sources_count=len(source_items),
                evidence=[
                    item.url or item.external_url
                    for item in source_items
                    if item.url or item.external_url
                ][:CONTENT_PLAN_MAX_EVIDENCE_URLS],
                raw_json={
                    "batch_summaries": batch_summaries,
                    "source_item_ids": [item.id for item in source_items],
                },
                status="ready",
            )

    @staticmethod
    def _save_plan_items(
        normalized: list[dict[str, Any]],
    ) -> list[ContentPlan]:
        with session_scope() as session:
            repo = ReportsRepository(session)
            return [
                repo.create_content_plan_item(item)
                for item in normalized
            ]

    @staticmethod
    def _deduplicate(values: list[Any]) -> list[Any]:
        result: list[Any] = []
        seen: set[str] = set()
        for value in values:
            marker = str(value)
            if marker and marker not in seen:
                seen.add(marker)
                result.append(value)
        return result

    @staticmethod
    def _list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    async def intelligence_status(self) -> dict[str, bool]:
        def load() -> dict[str, bool]:
            with session_scope() as session:
                reports = ReportsRepository(session)
                return {
                    "source_items": bool(
                        session.scalar(select(SourceItem.id).limit(1))
                    ),
                    "market_scan": reports.latest_report("market_scan") is not None,
                    "competitor_report": (
                        reports.latest_report("competitor_report") is not None
                        or reports.latest_report("competitor") is not None
                    ),
                }

        return await asyncio.to_thread(load)

    async def list_draft_items(self, limit: int = 20) -> list[ContentPlan]:
        def load() -> list[ContentPlan]:
            with session_scope() as session:
                return ReportsRepository(session).list_draft_plan_items(limit)

        return await asyncio.to_thread(load)

    async def get_item(self, item_id: int) -> ContentPlan | None:
        def load() -> ContentPlan | None:
            with session_scope() as session:
                return ReportsRepository(session).get_content_plan_item(item_id)

        return await asyncio.to_thread(load)

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        required = (
            "publish_date",
            "channel",
            "content_type",
            "topic",
            "goal",
            "target_audience",
            "key_message",
            "cta",
            "source_idea",
            "why_recommended",
        )
        missing = [key for key in required if not str(item.get(key, "")).strip()]
        if missing:
            raise AIServiceError(
                f"Content plan item is missing required fields: {', '.join(missing)}."
            )
        try:
            parsed_date = datetime.fromisoformat(
                str(item["publish_date"]).replace("Z", "+00:00")
            )
        except ValueError:
            try:
                date_value = datetime.strptime(
                    str(item["publish_date"]), "%Y-%m-%d"
                ).date()
                parsed_date = datetime.combine(date_value, time(hour=9))
            except ValueError as exc:
                raise AIServiceError("Content plan contains an invalid date.") from exc
        return {
            "publish_date": parsed_date,
            "channel": str(item["channel"]).strip(),
            "content_type": str(item["content_type"]).strip(),
            "topic": str(item["topic"]).strip(),
            "goal": str(item["goal"]).strip(),
            "target_audience": str(item["target_audience"]).strip(),
            "key_message": str(item["key_message"]).strip(),
            "cta": str(item["cta"]).strip(),
            "source_idea": str(item["source_idea"]).strip(),
            "why_recommended": str(item["why_recommended"]).strip(),
            "status": "draft",
        }

    @staticmethod
    def _save_page_id(item_id: int, page_id: str) -> None:
        with session_scope() as session:
            item = session.get(ContentPlan, item_id)
            if item:
                item.notion_page_id = page_id
