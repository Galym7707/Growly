from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any, Awaitable, Callable

from sqlalchemy import desc, select

from app.database import session_scope
from app.models import (
    ContentPlan,
    Report,
    Setting,
    SourceItem,
)
from app.repositories.market_scan_jobs_repo import MarketScanJobsRepository
from app.repositories.reports_repo import ReportsRepository
from app.services.ai_service import AIService
from app.services.market_context import build_market_context
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

_NICHE_WORD = {"ru": "ниши", "en": "the niche", "kk": "нишаның"}
_FALLBACK_GOALS = {
    "ru": [
        "Получить больше заявок",
        "Повысить доверие к бренду",
        "Продать ключевую услугу",
        "Объяснить ценность предложения",
    ],
    "en": [
        "Get more leads",
        "Build brand trust",
        "Sell the core service",
        "Explain the value proposition",
    ],
    "kk": [
        "Көбірек өтінім алу",
        "Брендке сенімді арттыру",
        "Негізгі қызметті сату",
        "Ұсыныс құндылығын түсіндіру",
    ],
}
_FALLBACK_AUDIENCES = {
    "ru": [
        "Малый и средний бизнес",
        "Владельцы интернет-магазинов",
        "Новые потенциальные клиенты",
        "Постоянные клиенты для повторных продаж",
    ],
    "en": [
        "Small and medium business",
        "Online store owners",
        "New potential clients",
        "Returning clients for repeat sales",
    ],
    "kk": [
        "Шағын және орта бизнес",
        "Интернет-дүкен иелері",
        "Жаңа әлеуетті клиенттер",
        "Қайта сатуға арналған тұрақты клиенттер",
    ],
}
_FALLBACK_OFFERS = {
    "ru": [
        "Основная услуга для ниши «{topic}»",
        "Пробное предложение со скидкой",
        "Комплексный пакет услуг",
        "Консультация по теме «{topic}»",
    ],
    "en": [
        "Core service for the «{topic}» niche",
        "Discounted trial offer",
        "Bundled service package",
        "Consultation about «{topic}»",
    ],
    "kk": [
        "«{topic}» нишасына негізгі қызмет",
        "Жеңілдікпен сынақ ұсынысы",
        "Кешенді қызмет пакеті",
        "«{topic}» бойынша кеңес",
    ],
}
_FALLBACK_CONTENT_TYPES = {
    "ru": [
        "Пост",
        "Reels / короткое видео",
        "Stories",
        "Кейс клиента",
        "FAQ / ответы на вопросы",
    ],
    "en": [
        "Post",
        "Reels / short video",
        "Stories",
        "Customer case",
        "FAQ",
    ],
    "kk": [
        "Пост",
        "Reels / қысқа видео",
        "Stories",
        "Клиент кейсі",
        "Жиі қойылатын сұрақтар",
    ],
}
_FALLBACK_CTAS = {
    "ru": [
        "Оставить заявку",
        "Получить консультацию",
        "Узнать стоимость",
        "Написать в Telegram",
    ],
    "en": [
        "Leave a request",
        "Get a consultation",
        "Find out the price",
        "Message us on Telegram",
    ],
    "kk": [
        "Өтінім қалдыру",
        "Кеңес алу",
        "Бағасын білу",
        "Telegram-ға жазу",
    ],
}


class ContentPlanService:
    def __init__(
        self,
        ai: AIService | None = None,
        notion: NotionService | None = None,
        groq: AIService | None = None,
    ) -> None:
        self.ai = ai or groq or AIService()
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
            response = await self.ai.generate_content_plan(context)
        except AIServiceError as exc:
            if exc.status != 413:
                raise
            self.reduced_context_used = True
            logger.warning(
                "Content plan payload was rejected with 413; retrying with "
                "report-summary-only context."
            )
            response = await self.ai.generate_content_plan(
                self._summary_only_context(context)
            )
        payload = parse_json_response(response)
        if not isinstance(payload, list):
            raise AIServiceError("The content plan response was not a JSON array.")
        normalized = [
            self._normalize_item(item) for item in payload if isinstance(item, dict)
        ]
        normalized = self._ensure_current_plan_dates(normalized)
        thresholds = await asyncio.to_thread(self._load_thresholds)
        self._validate_mix(normalized, thresholds)

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
            response = await self.ai.summarize_content_plan_sources(
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
    def _validate_mix(
        items: list[dict[str, Any]],
        thresholds: dict[str, Any],
    ) -> None:
        video_tokens = ("reels", "short", "video", "ролик", "видео")
        post_tokens = ("telegram", "instagram", "post", "пост")
        digest_tokens = ("digest", "дайджест")

        def descriptor(item: dict[str, Any]) -> str:
            return f"{item.get('channel', '')} {item.get('content_type', '')}".lower()

        def is_video(item: dict[str, Any]) -> bool:
            return any(token in descriptor(item) for token in video_tokens)

        short_videos = sum(1 for item in items if is_video(item))
        posts = sum(
            1
            for item in items
            if any(token in descriptor(item) for token in post_tokens)
            and not is_video(item)
        )
        whatsapp = sum(1 for item in items if "whatsapp" in descriptor(item))
        digest = sum(
            1 for item in items if any(token in descriptor(item) for token in digest_tokens)
        )

        problems: list[str] = []
        if posts < thresholds["min_posts"]:
            problems.append(f"posts {posts}/{thresholds['min_posts']}")
        if short_videos < thresholds["min_videos"]:
            problems.append(f"videos {short_videos}/{thresholds['min_videos']}")
        if thresholds.get("require_whatsapp") and whatsapp < 1:
            problems.append("missing WhatsApp message")
        if thresholds.get("require_digest") and digest < 1:
            problems.append("missing weekly digest")
        if problems:
            raise AIServiceError(
                "Content plan does not meet the configured mix: "
                + ", ".join(problems)
                + "."
            )

    CONTENT_PLAN_SETTING_KEYS = (
        "content_plan_min_posts",
        "content_plan_min_videos",
        "content_plan_require_whatsapp",
        "content_plan_require_digest",
    )

    @staticmethod
    def _as_bool(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}

    @staticmethod
    def _thresholds_from_settings(raw: dict[str, Any]) -> dict[str, Any]:
        def as_int(key: str, default: int) -> int:
            try:
                return int(str(raw.get(key)).strip())
            except (TypeError, ValueError):
                return default

        return {
            "min_posts": as_int("content_plan_min_posts", 5),
            "min_videos": as_int("content_plan_min_videos", 2),
            "require_whatsapp": ContentPlanService._as_bool(
                raw.get("content_plan_require_whatsapp", False)
            ),
            "require_digest": ContentPlanService._as_bool(
                raw.get("content_plan_require_digest", False)
            ),
        }

    def _load_thresholds(self) -> dict[str, Any]:
        from app.repositories.settings_repo import SettingsRepository

        try:
            with session_scope() as session:
                raw = SettingsRepository(session).get_many(
                    list(self.CONTENT_PLAN_SETTING_KEYS)
                )
        except Exception:
            logger.warning(
                "Could not read content-plan thresholds from settings; "
                "using TZ defaults."
            )
            raw = {}
        return self._thresholds_from_settings(raw)

    def _load_context_data(
        self, business_context: dict[str, Any] | str | None
    ) -> dict[str, Any]:
        with session_scope() as session:
            reports_repo = ReportsRepository(session)
            brief = business_context if isinstance(business_context, dict) else {}
            use_market_context = brief.get("use_market_context", True) is not False
            selected_context = (
                brief.get("market_context")
                if isinstance(brief.get("market_context"), dict)
                else None
            )
            selected_report_id = (
                selected_context.get("report_id")
                if selected_context
                else None
            )
            latest_market_scan = None
            if selected_report_id:
                candidate = reports_repo.get_report(int(selected_report_id))
                if candidate and candidate.report_type == "market_scan":
                    latest_market_scan = candidate
            elif use_market_context and selected_context is None:
                latest_market_scan = reports_repo.latest_report("market_scan")

            active_market_context = (
                self._market_context_from_report(latest_market_scan)
                if latest_market_scan
                else selected_context
            )
            source_item_ids = [
                int(item_id)
                for item_id in (
                    (active_market_context or {}).get("source_item_ids") or []
                )
                if str(item_id).isdigit()
            ]
            source_items = (
                list(
                    session.scalars(
                        select(SourceItem)
                        .where(SourceItem.id.in_(source_item_ids))
                        .order_by(desc(SourceItem.collected_at))
                    )
                )
                if source_item_ids
                else []
            )
            latest_competitor_report = (
                reports_repo.latest_report("competitor_report")
                or reports_repo.latest_report("competitor")
            )
            competitor_payload = (
                latest_competitor_report.raw_json
                if latest_competitor_report
                and isinstance(latest_competitor_report.raw_json, dict)
                else {}
            )
            active_report_id = (active_market_context or {}).get("report_id")
            if (
                not active_report_id
                or competitor_payload.get("market_report_id") != active_report_id
            ):
                latest_competitor_report = None
            settings = list(
                session.scalars(
                    select(Setting)
                    .where(Setting.key.like("business_%"))
                    .order_by(Setting.key)
                )
            )
            profile = {row.key: row.value for row in settings}
            requested_business = (
                brief.get("business") if isinstance(brief.get("business"), dict) else {}
            )
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
                    *((active_market_context or {}).get("source_urls") or []),
                    *[
                        item.url or item.external_url
                        for item in source_items
                        if item.url or item.external_url
                    ],
                ]
            )[:CONTENT_PLAN_MAX_EVIDENCE_URLS]
            today = datetime.now(UTC).date()
            return {
                "weekly_objective": business_context
                or {"note": "No additional brief supplied."},
                "current_date": today.isoformat(),
                "planning_window": {
                    "start": today.isoformat(),
                    "end": (today + timedelta(days=6)).isoformat(),
                },
                "business": {
                    "niche": (
                        requested_business.get("niche")
                        or requested_business.get("business_niche")
                        or (active_market_context or {}).get("category")
                        or (active_market_context or {}).get("topic")
                        or profile.get("business_niche")
                    ),
                    "region": (
                        requested_business.get("region")
                        or requested_business.get("business_region")
                        or (active_market_context or {}).get("region")
                        or profile.get("business_region")
                    ),
                    "language": (
                        requested_business.get("language")
                        or brief.get("language")
                        or requested_business.get("business_language")
                        or (active_market_context or {}).get("language")
                        or profile.get("business_language")
                    ),
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
                            latest_market_scan.summary if latest_market_scan else ""
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
                        "market_context": active_market_context,
                    }
                    if active_market_context
                    else None
                ),
                "evidence_limited": not bool(
                    source_items or latest_competitor_report or active_market_context
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

    CONTENT_PLAN_OPTION_KEYS = (
        "goals",
        "audiences",
        "offers",
        "channels",
        "content_types",
        "ctas",
    )

    async def generate_content_plan_options(
        self,
        report_id: int,
        language: str = "ru",
    ) -> dict[str, list[dict[str, str]]]:
        report = await asyncio.to_thread(self._load_report, report_id)
        if report is None:
            raise ValueError("Отчёт не найден.")
        context = self._content_plan_options_context(report, language)
        options: dict[str, list[dict[str, str]]]
        try:
            response = await self.ai.generate_content_plan_options(context)
            payload = parse_json_response(response)
            options = self._normalize_options(payload)
        except (AIServiceError, ConfigurationError, ValueError, TimeoutError):
            logger.warning(
                "Content plan options AI generation failed for report %s; "
                "using report-derived fallback.",
                report_id,
            )
            options = {}
        merged = self._fallback_options(context, language)
        for key in self.CONTENT_PLAN_OPTION_KEYS:
            generated = options.get(key) or []
            merged[key] = generated[:6] if generated else merged[key]
        if not merged.get("channels"):
            merged["channels"] = self._default_channels()
        return merged

    @staticmethod
    def _load_report(report_id: int) -> Report | None:
        with session_scope() as session:
            return ReportsRepository(session).get_report(report_id)

    @classmethod
    def _content_plan_options_context(
        cls,
        report: Report,
        language: str,
    ) -> dict[str, Any]:
        raw = report.raw_json if isinstance(report.raw_json, dict) else {}
        market_context = cls._market_context_from_report(report)
        topic = str(
            market_context.get("topic") or report.query or report.title or ""
        ).strip()

        def field(*names: str) -> list[Any]:
            for name in names:
                value = raw.get(name)
                if isinstance(value, list) and value:
                    return value[:12]
            return []

        return {
            "language": language,
            "topic": topic,
            "niche": topic,
            "region": market_context.get("region"),
            "report_type": report.report_type,
            "summary": str(report.summary or "")[:1200],
            "audience_pains": field("audience_pains"),
            "repeated_offers": field("repeated_offers", "repeating_offers"),
            "repeated_ctas": field("repeated_ctas", "repeating_ctas"),
            "content_gaps": field("content_gaps"),
            "content_ideas": field("content_ideas"),
            "dominant_topics": field("dominant_topics"),
            "weekly_priorities": field("weekly_priorities", "actions_this_week"),
            "recommendations": [
                str(value)
                for value in (getattr(report, "recommendations_json", None) or [])
                if str(value).strip()
            ][:12],
        }

    @classmethod
    def _normalize_options(
        cls,
        payload: Any,
    ) -> dict[str, list[dict[str, str]]]:
        if not isinstance(payload, dict):
            return {}
        result: dict[str, list[dict[str, str]]] = {}
        for key in cls.CONTENT_PLAN_OPTION_KEYS:
            items = payload.get(key)
            if not isinstance(items, list):
                continue
            normalized: list[dict[str, str]] = []
            seen: set[str] = set()
            for item in items:
                option = cls._normalize_option(item, channel=key == "channels")
                if option is None:
                    continue
                marker = option["label"].casefold()
                if marker in seen:
                    continue
                seen.add(marker)
                normalized.append(option)
            if normalized:
                result[key] = normalized[:6]
        return result

    @staticmethod
    def _normalize_option(
        item: Any,
        *,
        channel: bool = False,
    ) -> dict[str, str] | None:
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("value") or "").strip()
            value = str(item.get("value") or item.get("label") or "").strip()
        elif isinstance(item, str):
            label = value = item.strip()
        else:
            return None
        if not label:
            return None
        label = label[:60]
        if channel and value:
            value = value.strip().lower().replace(" ", "_")
        return {"label": label, "value": value or label}

    @classmethod
    def _fallback_options(
        cls,
        context: dict[str, Any],
        language: str,
    ) -> dict[str, list[dict[str, str]]]:
        topic = str(context.get("topic") or "").strip()
        lang = language if language in {"ru", "en", "kk"} else "ru"

        def options_from(values: list[Any]) -> list[dict[str, str]]:
            result: list[dict[str, str]] = []
            seen: set[str] = set()
            for value in values:
                text = str(value).strip()
                if not text or text.casefold() in seen:
                    continue
                seen.add(text.casefold())
                result.append({"label": text[:60], "value": text})
                if len(result) >= 6:
                    break
            return result

        def templated(items: list[str]) -> list[dict[str, str]]:
            result: list[dict[str, str]] = []
            for raw_item in items:
                text = raw_item.replace("{topic}", topic or _NICHE_WORD[lang])
                result.append({"label": text[:60], "value": text})
            return result

        offers = options_from(context.get("repeated_offers") or [])
        ctas = options_from(context.get("repeated_ctas") or [])
        return {
            "goals": templated(_FALLBACK_GOALS[lang]),
            "audiences": templated(_FALLBACK_AUDIENCES[lang]),
            "offers": offers or templated(_FALLBACK_OFFERS[lang]),
            "channels": cls._default_channels(),
            "content_types": templated(_FALLBACK_CONTENT_TYPES[lang]),
            "ctas": ctas or templated(_FALLBACK_CTAS[lang]),
        }

    @staticmethod
    def _default_channels() -> list[dict[str, str]]:
        return [
            {"label": "Instagram", "value": "instagram"},
            {"label": "Telegram", "value": "telegram"},
            {"label": "WhatsApp", "value": "whatsapp"},
            {"label": "Сайт", "value": "website"},
        ]

    async def latest_market_context(
        self,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._load_market_context,
            None,
            user_id,
        )

    async def market_context_for_report(
        self,
        report_id: int,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._load_market_context,
            report_id,
            None,
        )

    @classmethod
    def _load_market_context(
        cls,
        report_id: int | None,
        user_id: int | None,
    ) -> dict[str, Any] | None:
        with session_scope() as session:
            reports = ReportsRepository(session)
            if report_id is not None:
                report = reports.get_report(report_id)
            elif user_id is not None:
                job = MarketScanJobsRepository(session).latest_for_user(user_id)
                report = (
                    reports.get_report(job.report_id)
                    if job and job.report_id
                    else None
                )
            else:
                report = reports.latest_report("market_scan")
            if report is None or report.report_type != "market_scan":
                return None
            return cls._market_context_from_report(report)

    @staticmethod
    def _market_context_from_report(report: Report) -> dict[str, Any]:
        payload = report.raw_json if isinstance(report.raw_json, dict) else {}
        stored = (
            payload.get("market_context")
            if isinstance(payload.get("market_context"), dict)
            else {}
        )
        source_item_ids = [
            int(item_id)
            for item_id in payload.get("source_item_ids", [])
            if str(item_id).isdigit()
        ]
        context = build_market_context(
            str(stored.get("topic") or report.query or report.title or ""),
            str(stored.get("region_language") or ""),
            report_id=report.id,
            source_item_ids=source_item_ids,
            source_urls=[
                str(url)
                for url in (report.evidence_json or [])
                if str(url).strip()
            ],
            sources_count=report.sources_count,
        )
        for key in ("region", "language", "category", "category_code"):
            if stored.get(key):
                context[key] = stored[key]
        return context

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
    def _ensure_current_plan_dates(
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date()
        for index, item in enumerate(items):
            value = item.get("publish_date")
            if not isinstance(value, datetime) or value.date() >= today:
                continue
            replacement_date = today + timedelta(days=index % 7)
            replacement_time = time(hour=9 + min(index % 6, 5))
            item["publish_date"] = datetime.combine(
                replacement_date,
                replacement_time,
                tzinfo=value.tzinfo,
            )
        return items

    @staticmethod
    def _save_page_id(item_id: int, page_id: str) -> None:
        with session_scope() as session:
            item = session.get(ContentPlan, item_id)
            if item:
                item.notion_page_id = page_id
