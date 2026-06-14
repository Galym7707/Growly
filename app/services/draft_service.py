from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import ContentPlan, Draft, Publication
from app.repositories.drafts_repo import DraftsRepository
from app.repositories.users_repo import UsersRepository
from app.services.ai_service import AIService
from app.services.notion_service import NotionService
from app.services.content_types import (
    ContentTypeSpec,
    CONTENT_TYPE_BY_KEY,
    detect_content_type,
    normalize_content_type,
)
from app.utils.errors import NotionServiceError
from app.utils.errors import AIServiceError
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)

GENERIC_OPENINGS = (
    "устали тратить время",
    "мы предлагаем качественные услуги",
    "наша компания поможет",
    "ищете надежного партнера",
    "ищете надёжного партнера",
)

UNSUPPORTED_CLAIM_PATTERNS = (
    (r"\bскид\w*", r"\bскид\w*"),
    (r"\bdiscount\w*", r"\bdiscount\w*"),
    (r"гарантирован\w*\s+эконом\w*", r"гарантирован\w*\s+эконом\w*"),
    (r"guaranteed\s+savings?", r"guaranteed\s+savings?"),
    (r"достав\w*\s+(?:в\s+тот\s+же|за\s+один)\s+день", r"достав\w*"),
    (r"same[- ]day\s+delivery", r"same[- ]day\s+delivery"),
    (r"сам\w*\s+низк\w*\s+цен\w*", r"сам\w*\s+низк\w*\s+цен\w*"),
    (r"lowest\s+price", r"lowest\s+price"),
    (
        r"гарант\w*(?:\s+\w+){0,2}\s+(?:лид\w*|продаж\w*)",
        r"гарант\w*(?:\s+\w+){0,2}\s+(?:лид\w*|продаж\w*)",
    ),
    (
        r"guarante\w*(?:\s+\w+){0,2}\s+(?:leads?|sales?)",
        r"guarante\w*(?:\s+\w+){0,2}\s+(?:leads?|sales?)",
    ),
)


@dataclass(slots=True)
class PublicationReservation:
    publication: Publication
    should_publish: bool


class DraftService:
    def __init__(
        self,
        settings: Settings | None = None,
        groq: AIService | None = None,
        notion: NotionService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.groq = groq or AIService(self.settings)
        self.notion = notion or NotionService(self.settings)

    async def create_asset_post(self, context: dict[str, Any]) -> Draft:
        return await self._create_typed_draft(
            context, CONTENT_TYPE_BY_KEY["asset_post"]
        )

    async def create_case_post(self, context: dict[str, Any]) -> Draft:
        return await self._create_typed_draft(
            context, CONTENT_TYPE_BY_KEY["case_post"]
        )

    async def create_post(self, context: dict[str, Any]) -> Draft:
        brief = str(context.get("brief") or "")
        spec = detect_content_type(brief)
        return await self._create_typed_draft(context, spec)

    async def _create_typed_draft(
        self,
        context: dict[str, Any],
        spec: ContentTypeSpec,
        *,
        content_plan_id: int | None = None,
    ) -> Draft:
        channel = self._requested_channel(context)
        enriched_context = {
            **context,
            "requested_content_type": spec.label,
            "draft_type": spec.key,
            "channel": channel,
        }
        requested_cta = self._requested_cta(enriched_context)
        if requested_cta:
            enriched_context["cta"] = requested_cta
        payload = await self._generate_structured(enriched_context, spec)
        return await self._save_new(
            draft_type=spec.key,
            channel=channel,
            title=str(
                context.get("title")
                or context.get("topic")
                or spec.label
            ),
            draft_text=payload["draft_text"],
            prompt_name=spec.prompt_name,
            original_context=enriched_context,
            generation_metadata=self._metadata(payload),
            content_plan_id=content_plan_id,
        )

    async def create_from_plan(self, item_id: int) -> Draft:
        def load() -> ContentPlan | None:
            with session_scope() as session:
                return session.get(ContentPlan, item_id)

        item = await asyncio.to_thread(load)
        if item is None:
            raise ValueError("Content plan item was not found.")
        context = {
            "content_plan": {
                "id": item.id,
                "publish_date": item.publish_date,
                "channel": item.channel,
                "content_type": item.content_type,
                "topic": item.topic,
                "goal": item.goal,
                "target_audience": item.target_audience,
                "key_message": item.key_message,
                "cta": item.cta,
                "source_idea": item.source_idea,
                "why_recommended": item.why_recommended,
            }
        }
        spec = normalize_content_type(item.content_type)
        draft = await self._create_typed_draft(
            {
                **context,
                "channel": item.channel or "Telegram",
                "title": item.topic or f"Content plan item {item.id}",
                "cta": item.cta,
            },
            spec,
            content_plan_id=item.id,
        )

        def mark_drafted() -> None:
            with session_scope() as session:
                current = session.get(ContentPlan, item.id)
                if current:
                    current.status = "drafted"

        await asyncio.to_thread(mark_drafted)
        return draft

    async def _save_new(
        self,
        *,
        draft_type: str,
        channel: str,
        title: str,
        draft_text: str,
        prompt_name: str,
        original_context: dict[str, Any],
        generation_metadata: dict[str, Any] | None = None,
        content_plan_id: int | None = None,
    ) -> Draft:
        def save() -> Draft:
            with session_scope() as session:
                return DraftsRepository(session).create(
                    draft_type=draft_type,
                    channel=channel,
                    title=title,
                    draft_text=draft_text,
                    ai_model=(
                        getattr(self.groq, "last_model_name", None)
                        or self.settings.ai_model_name()
                    ),
                    prompt_name=prompt_name,
                    original_context=original_context,
                    generation_metadata=generation_metadata,
                    content_plan_id=content_plan_id,
                )

        draft = await asyncio.to_thread(save)
        await self._safe_sync(draft)
        return draft

    async def get(self, draft_id: int) -> Draft | None:
        def load() -> Draft | None:
            with session_scope() as session:
                return DraftsRepository(session).get(draft_id)

        return await asyncio.to_thread(load)

    async def list_pending(self, limit: int = 20) -> list[Draft]:
        def load() -> list[Draft]:
            with session_scope() as session:
                return DraftsRepository(session).list_pending(limit)

        return await asyncio.to_thread(load)

    async def regenerate(self, draft_id: int) -> Draft:
        draft = await self.get(draft_id)
        if draft is None:
            raise ValueError("Draft was not found.")
        context = dict(draft.original_context_json or {})
        spec = normalize_content_type(draft.draft_type)
        payload = await self._generate_structured(
            {
                **context,
                "requested_content_type": spec.label,
                "draft_type": spec.key,
                "channel": draft.channel,
                "previous_draft": draft.draft_text,
                "instruction": "Create a materially improved new version.",
            },
            spec,
        )

        def update() -> Draft:
            with session_scope() as session:
                repo = DraftsRepository(session)
                current = repo.get(draft_id)
                if current is None:
                    raise ValueError("Draft was not found.")
                return repo.replace_generated_content(
                    current,
                    payload["draft_text"],
                    self._metadata(payload),
                )

        updated = await asyncio.to_thread(update)
        await self._safe_sync(updated)
        return updated

    async def record_action(
        self,
        *,
        draft_id: int,
        telegram_chat_id: str,
        action: str,
        approved_by: str | None = None,
        comment: str | None = None,
    ) -> Draft:
        status_map = {"approve": "approved", "reject": "rejected"}
        if action not in status_map:
            raise ValueError("Unsupported draft action.")

        def update() -> Draft:
            with session_scope() as session:
                drafts = DraftsRepository(session)
                users = UsersRepository(session)
                draft = drafts.get(draft_id)
                if draft is None:
                    raise ValueError("Draft was not found.")
                if action == "approve" and draft.status in {"approved", "published"}:
                    return draft
                if action == "reject" and draft.status == "published":
                    raise ValueError("Published drafts cannot be rejected.")
                user = users.get_by_chat_id(telegram_chat_id)
                drafts.update_status(
                    draft, status_map[action], approved_by if action == "approve" else None
                )
                drafts.add_approval(
                    draft=draft, action=action, user=user, comment=comment
                )
                return draft

        draft = await asyncio.to_thread(update)
        await self._safe_sync(draft)
        return draft

    async def set_telegram_message(self, draft_id: int, message_id: int) -> None:
        def update() -> None:
            with session_scope() as session:
                repo = DraftsRepository(session)
                draft = repo.get(draft_id)
                if draft:
                    repo.set_telegram_message(draft, message_id)

        await asyncio.to_thread(update)

    async def record_event(
        self,
        *,
        draft_id: int,
        telegram_chat_id: str,
        action: str,
        comment: str | None = None,
    ) -> None:
        def save() -> None:
            with session_scope() as session:
                drafts = DraftsRepository(session)
                users = UsersRepository(session)
                draft = drafts.get(draft_id)
                if draft is None:
                    raise ValueError("Draft was not found.")
                drafts.add_approval(
                    draft=draft,
                    action=action,
                    user=users.get_by_chat_id(telegram_chat_id),
                    comment=comment,
                )

        await asyncio.to_thread(save)

    async def reserve_publication(
        self, draft_id: int, channel: str = "Telegram"
    ) -> PublicationReservation:
        def reserve() -> PublicationReservation:
            with session_scope() as session:
                draft = session.scalar(
                    select(Draft).where(Draft.id == draft_id).with_for_update()
                )
                if draft is None:
                    raise ValueError("Draft was not found.")
                if draft.status not in {"approved", "published"}:
                    raise ValueError("Only approved drafts can be published.")
                publication = session.scalar(
                    select(Publication).where(
                        Publication.draft_id == draft.id,
                        Publication.channel == channel,
                    )
                )
                if publication is not None and publication.status in {
                    "publishing",
                    "published",
                }:
                    return PublicationReservation(
                        publication=publication,
                        should_publish=False,
                    )
                if publication is None:
                    publication = Publication(
                        draft_id=draft.id,
                        channel=channel,
                        status="publishing",
                        metrics_json={},
                    )
                    session.add(publication)
                else:
                    publication.status = "publishing"
                    publication.metrics_json = {}
                session.flush()
                return PublicationReservation(
                    publication=publication,
                    should_publish=True,
                )

        return await asyncio.to_thread(reserve)

    async def complete_publication(
        self, publication_id: int, message_ids: list[int]
    ) -> Publication:
        def complete() -> Publication:
            with session_scope() as session:
                publication = session.get(Publication, publication_id)
                if publication is None:
                    raise ValueError("Publication was not found.")
                draft = session.get(Draft, publication.draft_id)
                if draft is None:
                    raise ValueError("Draft was not found.")
                publication.status = "published"
                publication.published_at = datetime.now(UTC)
                publication.metrics_json = {
                    "telegram_message_ids": message_ids,
                    "parts": len(message_ids),
                }
                publication.telegram_message_id = ",".join(map(str, message_ids))
                draft.status = "published"
                session.flush()
                return publication

        publication = await asyncio.to_thread(complete)
        try:
            await self.notion.sync_publication(publication)
            draft = await self.get(publication.draft_id)
            if draft:
                await self._safe_sync(draft)
        except NotionServiceError:
            logger.warning("Publication %s could not sync to Notion.", publication.id)
        return publication

    async def fail_publication(self, publication_id: int) -> None:
        def fail() -> None:
            with session_scope() as session:
                publication = session.get(Publication, publication_id)
                if publication and publication.status == "publishing":
                    publication.status = "failed"

        await asyncio.to_thread(fail)

    async def ensure_notion(self, draft_id: int) -> str:
        draft = await self.get(draft_id)
        if draft is None:
            raise ValueError("Draft was not found.")
        page = await self.notion.sync_draft(draft)
        page_id = page["id"]
        await self._save_notion_page(draft_id, page_id)
        return page.get("url") or self.notion.page_url(page_id)

    async def _safe_sync(self, draft: Draft) -> None:
        try:
            page = await self.notion.sync_draft(draft)
            if not draft.notion_page_id:
                await self._save_notion_page(draft.id, page["id"])
                draft.notion_page_id = page["id"]
        except NotionServiceError:
            logger.warning("Draft %s was saved but Notion sync failed.", draft.id)

    async def _save_notion_page(self, draft_id: int, page_id: str) -> None:
        def update() -> None:
            with session_scope() as session:
                repo = DraftsRepository(session)
                draft = repo.get(draft_id)
                if draft:
                    repo.set_notion_page(draft, page_id)

        await asyncio.to_thread(update)

    async def _generate_structured(
        self, context: dict[str, Any], spec: ContentTypeSpec
    ) -> dict[str, Any]:
        analysis = await self._analyze_brief(context, spec)
        generation_context = {
            **context,
            "requested_content_type": spec.label,
            "draft_type": spec.key,
            "brief_analysis": analysis,
            "quality_rules": {
                "preserve_cta": self._requested_cta(context, analysis),
                "forbidden_generic_openings": list(GENERIC_OPENINGS),
                "do_not_invent": [
                    "discounts",
                    "guaranteed savings",
                    "same-day delivery",
                    "lowest price",
                    "guaranteed leads or sales",
                ],
            },
        }
        violations: list[str] = []
        for attempt in range(2):
            if violations:
                generation_context["revision_required"] = violations
            response = await self.groq.generate_content_draft(
                spec.prompt_name, generation_context
            )
            payload = parse_json_response(response)
            self._validate_payload_shape(payload)
            violations = self._content_violations(
                payload,
                context=generation_context,
                analysis=analysis,
            )
            if not violations:
                payload["brief_analysis"] = analysis
                return payload
        raise AIServiceError(
            "Generated draft did not pass CTA and claim safety checks."
        )

    async def _analyze_brief(
        self, context: dict[str, Any], spec: ContentTypeSpec
    ) -> dict[str, Any]:
        response = await self.groq.analyze_draft_brief(
            {
                **context,
                "requested_content_type": spec.label,
                "draft_type": spec.key,
            }
        )
        analysis = parse_json_response(response)
        if not isinstance(analysis, dict):
            raise AIServiceError("Brief analysis response was not a JSON object.")
        required = (
            "product_service",
            "audience",
            "main_pain",
            "business_context",
            "channel",
            "cta",
            "allowed_claims",
            "forbidden_claims",
            "overpromising_risk",
        )
        missing = [key for key in required if key not in analysis]
        if missing:
            raise AIServiceError(
                "Brief analysis response is missing required fields."
            )
        if not isinstance(analysis["allowed_claims"], list) or not isinstance(
            analysis["forbidden_claims"], list
        ):
            raise AIServiceError("Brief claim analysis fields are invalid.")
        requested_cta = self._requested_cta(context)
        if requested_cta:
            analysis["cta"] = requested_cta
        analysis["channel"] = self._requested_channel(context)
        return analysis

    @staticmethod
    def _validate_payload_shape(payload: Any) -> None:
        if not isinstance(payload, dict):
            raise AIServiceError("Draft generation response was not a JSON object.")
        required = (
            "draft_text",
            "content_angle",
            "source_insight",
            "target_pain",
            "cta",
            "risk_check",
            "why_this_should_work",
        )
        missing = [
            key
            for key in required
            if key not in payload or not str(payload.get(key, "")).strip()
        ]
        if missing:
            raise AIServiceError(
                "Draft generation response is missing required strategic fields."
            )

    @classmethod
    def _content_violations(
        cls,
        payload: dict[str, Any],
        *,
        context: dict[str, Any],
        analysis: dict[str, Any],
    ) -> list[str]:
        draft_text = str(payload.get("draft_text") or "")
        normalized_draft = cls._normalize_text(draft_text)
        source_text = cls._normalize_text(
            " ".join(
                str(value)
                for key, value in context.items()
                if key not in {"brief_analysis", "quality_rules", "revision_required"}
            )
        )
        violations: list[str] = []
        opening = normalized_draft[:240]
        for phrase in GENERIC_OPENINGS:
            if cls._normalize_text(phrase) in opening:
                violations.append(f"Forbidden generic opening: {phrase}")

        for output_pattern, evidence_pattern in UNSUPPORTED_CLAIM_PATTERNS:
            if re.search(output_pattern, normalized_draft, flags=re.IGNORECASE) and not re.search(
                evidence_pattern, source_text, flags=re.IGNORECASE
            ):
                violations.append(
                    f"Unsupported claim matched pattern: {output_pattern}"
                )

        requested_cta = cls._requested_cta(context, analysis)
        if requested_cta and cls._normalize_text(requested_cta) not in normalized_draft:
            violations.append("The supplied CTA was not preserved in draft_text.")
        return violations

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower().replace("ё", "е"))

    @classmethod
    def _requested_cta(
        cls,
        context: dict[str, Any],
        analysis: dict[str, Any] | None = None,
    ) -> str | None:
        direct = context.get("cta")
        if direct and str(direct).strip():
            return str(direct).strip()
        content_plan = context.get("content_plan")
        if isinstance(content_plan, dict) and str(content_plan.get("cta") or "").strip():
            return str(content_plan["cta"]).strip()
        for field in ("brief", "case_details"):
            value = str(context.get(field) or "")
            match = re.search(
                r"(?im)^\s*(?:cta|призыв\s+к\s+действию)\s*[:\-]\s*(.+?)\s*$",
                value,
            )
            if match:
                return match.group(1).strip()
        if analysis:
            analyzed = str(analysis.get("cta") or "").strip()
            if analyzed.lower() not in {"", "not supplied", "не указано"}:
                return analyzed
        return None

    @staticmethod
    def _requested_channel(context: dict[str, Any]) -> str:
        direct = str(context.get("channel") or "").strip()
        if direct:
            return direct
        brief = str(context.get("brief") or "")
        match = re.search(
            r"(?im)^\s*(?:канал|channel)\s*[:\-]\s*(.+?)\s*$",
            brief,
        )
        return match.group(1).strip() if match else "Telegram"

    @staticmethod
    def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
        metadata = {
            key: payload.get(key)
            for key in (
                "content_angle",
                "source_insight",
                "target_pain",
                "cta",
                "risk_check",
                "why_this_should_work",
            )
        }
        metadata["brief_analysis"] = payload.get("brief_analysis") or {}
        return metadata
