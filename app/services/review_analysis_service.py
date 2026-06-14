from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.database import session_scope
from app.models import ReviewImport
from app.repositories.reports_repo import ReportsRepository
from app.services.ai_service import AIService
from app.services.notion_service import NotionService
from app.utils.errors import AIServiceError, NotionServiceError
from app.utils.text import parse_json_response

logger = logging.getLogger(__name__)


class ReviewAnalysisService:
    def __init__(
        self,
        groq: AIService | None = None,
        notion: NotionService | None = None,
    ) -> None:
        self.groq = groq or AIService()
        self.notion = notion or NotionService()

    async def analyze(
        self, raw_text: str, source_name: str = "Manual Telegram import"
    ) -> ReviewImport:
        clean_text = raw_text.strip()
        if len(clean_text) < 10:
            raise ValueError("Review text is too short to analyze.")
        response = await self.groq.analyze_reviews(
            {"source_name": source_name, "raw_text": clean_text}
        )
        payload = parse_json_response(response)
        if not isinstance(payload, dict):
            raise AIServiceError("Review analysis response was not a JSON object.")
        expected_arrays = (
            "pains",
            "objections",
            "repeated_questions",
            "trust_issues",
            "buying_triggers",
            "emotional_words",
            "customer_language_snippets",
            "content_opportunities",
            "faq_ideas",
            "risk_notes",
            "recommended_posts",
        )
        for key in expected_arrays:
            if not isinstance(payload.get(key, []), list):
                raise AIServiceError(f"Review analysis field {key} is invalid.")
        summary = self._format_summary(payload)
        title = f"Market insights: {datetime.now(UTC).date().isoformat()}"

        def save() -> ReviewImport:
            with session_scope() as session:
                return ReportsRepository(session).create_review_import(
                    title=title,
                    source_name=source_name,
                    raw_text=clean_text,
                    ai_summary=summary,
                    pains=payload.get("pains", []),
                    objections=payload.get("objections", []),
                    content_ideas=payload.get("content_opportunities", []),
                    repeated_questions=payload.get("repeated_questions", []),
                    trust_issues=payload.get("trust_issues", []),
                    buying_triggers=payload.get("buying_triggers", []),
                    emotional_words=payload.get("emotional_words", []),
                    customer_language=payload.get("customer_language_snippets", []),
                    faq_ideas=payload.get("faq_ideas", []),
                    risk_notes=payload.get("risk_notes", []),
                    recommended_posts=payload.get("recommended_posts", []),
                )

        review = await asyncio.to_thread(save)
        try:
            page = await self.notion.sync_review(review)
            await asyncio.to_thread(self._save_page_id, review.id, page["id"])
            review.notion_page_id = page["id"]
        except NotionServiceError:
            logger.warning("Review analysis %s could not sync to Notion.", review.id)
        return review

    @staticmethod
    def _format_summary(payload: dict[str, Any]) -> str:
        sections = [
            ("Summary", [payload.get("summary", "")]),
            ("Main pains", payload.get("pains", [])),
            ("Objections", payload.get("objections", [])),
            ("Repeated questions", payload.get("repeated_questions", [])),
            ("Trust issues", payload.get("trust_issues", [])),
            ("Buying triggers", payload.get("buying_triggers", [])),
            ("Emotional words", payload.get("emotional_words", [])),
            (
                "Exact customer language",
                payload.get("customer_language_snippets", []),
            ),
            ("Content opportunities", payload.get("content_opportunities", [])),
            ("FAQ ideas", payload.get("faq_ideas", [])),
            ("Risk notes", payload.get("risk_notes", [])),
            ("Recommended posts", payload.get("recommended_posts", [])),
        ]
        rendered: list[str] = []
        for heading, values in sections:
            clean_values = [str(value).strip() for value in values if str(value).strip()]
            rendered.append(f"{heading}\n" + "\n".join(f"- {value}" for value in clean_values))
        return "\n\n".join(rendered)

    @staticmethod
    def _save_page_id(review_id: int, page_id: str) -> None:
        with session_scope() as session:
            review = session.get(ReviewImport, review_id)
            if review:
                review.notion_page_id = page_id
