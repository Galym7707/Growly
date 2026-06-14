from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.database import session_scope
from app.repositories.logs_repo import LogsRepository
from app.utils.errors import AIServiceError

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MAX_ATTEMPTS = 3
GROQ_MAX_RETRY_DELAY_SECONDS = 60.0
GROQ_REQUEST_TIMEOUT_SECONDS = 60.0
GROQ_MAX_SOURCE_ITEMS = 8
GROQ_MAX_SNIPPET_CHARS = 300
GROQ_MAX_EVIDENCE_URLS = 10
GROQ_MAX_REPORT_CONTEXT_CHARS = 4000


def load_prompt(prompt_name: str) -> str:
    safe_name = Path(prompt_name).name
    path = PROMPTS_DIR / safe_name
    if path.suffix != ".md" or not path.is_file():
        raise FileNotFoundError(f"Prompt {safe_name!r} was not found.")
    return path.read_text(encoding="utf-8")


class GroqService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def _record_failure(self, message: str, details: dict[str, Any]) -> None:
        def write_log() -> None:
            try:
                with session_scope() as session:
                    LogsRepository(session).create(
                        level="ERROR",
                        module="groq",
                        message=message,
                        details=details,
                    )
            except Exception:
                logger.exception("Could not persist Groq integration error.")

        await asyncio.to_thread(write_log)

    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
    ) -> str:
        model = self.settings.require_text("groq_model", "GROQ_MODEL")
        template = load_prompt(prompt_name)
        context = self._apply_prompt_budget(context)
        context_json = (
            context
            if isinstance(context, str)
            else json.dumps(context, ensure_ascii=False, default=str)
        )
        logger.info(
            (
                "groq_payload_chars=%d source_items_used_count=%d "
                "evidence_urls_count=%d report_context_chars=%d prompt_name=%s"
            ),
            len(context_json),
            self._count_source_items(context),
            self._count_evidence_urls(context),
            self._count_report_context_chars(context),
            prompt_name,
        )
        prompt = template.replace("{context_json}", context_json)
        last_error: Exception | None = None
        try:
            for attempt in range(GROQ_MAX_ATTEMPTS):
                try:
                    async with httpx.AsyncClient(
                        timeout=GROQ_REQUEST_TIMEOUT_SECONDS
                    ) as client:
                        response = await client.post(
                            GROQ_CHAT_COMPLETIONS_URL,
                            headers={
                                "Authorization": f"Bearer {self.settings.groq_key()}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model,
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": (
                                            "Follow the task exactly. Never fabricate facts, "
                                            "metrics, quotes, customer evidence, or guarantees. "
                                            + self.settings.user_language_instruction()
                                        ),
                                    },
                                    {"role": "user", "content": prompt},
                                ],
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                            },
                        )
                    if response.status_code == 429 or response.status_code >= 500:
                        retry_after = self._retry_after_seconds(
                            response.headers.get("Retry-After")
                        )
                        last_error = AIServiceError(
                            f"Groq temporarily returned status {response.status_code}.",
                            status=response.status_code,
                            retry_after=retry_after,
                        )
                        if attempt < GROQ_MAX_ATTEMPTS - 1:
                            delay = max(2**attempt, retry_after or 0.0)
                            await asyncio.sleep(
                                min(delay, GROQ_MAX_RETRY_DELAY_SECONDS)
                            )
                            continue
                        raise last_error
                    response.raise_for_status()
                    payload = response.json()
                    content = payload["choices"][0]["message"]["content"]
                    if not content or not str(content).strip():
                        raise AIServiceError("Groq returned an empty response.")
                    return str(content).strip()
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt < GROQ_MAX_ATTEMPTS - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise
                except httpx.HTTPStatusError as exc:
                    raise AIServiceError(
                        f"Groq returned status {exc.response.status_code}.",
                        status=exc.response.status_code,
                    ) from exc
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise AIServiceError("Groq returned an invalid response.") from exc
        except Exception as exc:
            status = exc.status if isinstance(exc, AIServiceError) else None
            retry_after = (
                exc.retry_after if isinstance(exc, AIServiceError) else None
            )
            await self._record_failure(
                "Groq generation failed.",
                {
                    "exception_type": type(exc).__name__,
                    "prompt_name": prompt_name,
                    "status": status,
                },
            )
            if status == 429:
                raise AIServiceError(
                    "AI generation is delayed due to Groq rate limits.",
                    status=status,
                    retry_after=retry_after,
                ) from exc
            raise AIServiceError(
                "AI generation is temporarily unavailable. Please try again later.",
                status=status,
            ) from exc
        raise AIServiceError("AI generation did not complete.") from last_error

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value.strip()))
        except ValueError:
            pass
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def _apply_prompt_budget(cls, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for child_key, child_value in value.items():
                if child_key == "raw_json":
                    continue
                sanitized[child_key] = cls._apply_prompt_budget(
                    child_value,
                    child_key,
                )
            return sanitized
        if isinstance(value, list):
            rows = value
            if key in {"source_items", "recent_source_items"}:
                rows = rows[:GROQ_MAX_SOURCE_ITEMS]
            elif key in {"evidence_urls", "source_evidence"}:
                rows = rows[:GROQ_MAX_EVIDENCE_URLS]
            return [cls._apply_prompt_budget(item, key) for item in rows]
        if isinstance(value, str):
            if key in {"snippet", "raw_text", "content"}:
                return value[:GROQ_MAX_SNIPPET_CHARS]
            if key in {"body", "report_text", "report_context"}:
                return value[:GROQ_MAX_REPORT_CONTEXT_CHARS]
        return value

    @classmethod
    def _count_source_items(cls, value: Any) -> int:
        if isinstance(value, dict):
            return sum(
                len(child_value)
                if child_key in {"source_items", "recent_source_items"}
                and isinstance(child_value, list)
                else cls._count_source_items(child_value)
                for child_key, child_value in value.items()
            )
        if isinstance(value, list):
            return sum(cls._count_source_items(item) for item in value)
        return 0

    @classmethod
    def _count_evidence_urls(cls, value: Any) -> int:
        if isinstance(value, dict):
            return sum(
                len(child_value)
                if child_key in {"evidence_urls", "source_evidence"}
                and isinstance(child_value, list)
                else cls._count_evidence_urls(child_value)
                for child_key, child_value in value.items()
            )
        if isinstance(value, list):
            return sum(cls._count_evidence_urls(item) for item in value)
        return 0

    @classmethod
    def _count_report_context_chars(cls, value: Any) -> int:
        if isinstance(value, dict):
            return sum(
                len(child_value)
                if child_key in {"body", "report_text", "report_context"}
                and isinstance(child_value, str)
                else cls._count_report_context_chars(child_value)
                for child_key, child_value in value.items()
            )
        if isinstance(value, list):
            return sum(cls._count_report_context_chars(item) for item in value)
        return 0

    async def generate_asset_post(self, context: dict[str, Any]) -> str:
        return await self.generate_text("asset_post.md", context)

    async def generate_case_post(self, context: dict[str, Any]) -> str:
        return await self.generate_text("case_post.md", context)

    async def generate_content_plan(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "content_plan.md", context, temperature=0.3, max_tokens=4500
        )

    async def summarize_content_plan_sources(
        self,
        context: dict[str, Any],
    ) -> str:
        return await self.generate_text(
            "content_plan_source_batch.md",
            context,
            temperature=0.1,
            max_tokens=1400,
        )

    async def generate_competitor_report(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "competitor_report.md", context, temperature=0.2, max_tokens=4500
        )

    async def analyze_market_search(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "market_search_analysis.md", context, temperature=0.1, max_tokens=6000
        )

    async def extract_source_candidates(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "source_discovery.md", context, temperature=0.05, max_tokens=4500
        )

    async def summarize_source_monitoring(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "source_monitoring.md", context, temperature=0.1, max_tokens=5000
        )

    async def generate_market_scan(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "market_scan_report.md", context, temperature=0.1, max_tokens=6000
        )

    async def analyze_reviews(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "review_analysis.md", context, temperature=0.2, max_tokens=3500
        )

    async def analyze_source_items(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "source_item_analysis.md", context, temperature=0.15, max_tokens=5000
        )

    async def generate_draft_from_plan(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "draft_from_plan.md", context, temperature=0.25, max_tokens=4000
        )

    async def analyze_draft_brief(self, context: dict[str, Any]) -> str:
        return await self.generate_text(
            "brief_analysis.md", context, temperature=0.1, max_tokens=1800
        )

    async def generate_content_draft(
        self, prompt_name: str, context: dict[str, Any]
    ) -> str:
        return await self.generate_text(
            prompt_name, context, temperature=0.25, max_tokens=4000
        )

    async def generate_reels_script(self, context: dict[str, Any]) -> str:
        return await self.generate_text("reels_script.md", context)

    async def generate_whatsapp_message(self, context: dict[str, Any]) -> str:
        return await self.generate_text("whatsapp_message.md", context)

    async def generate_weekly_performance_report(
        self, context: dict[str, Any]
    ) -> str:
        return await self.generate_text(
            "weekly_performance_report.md", context, temperature=0.2
        )
