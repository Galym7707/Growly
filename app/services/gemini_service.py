"""Google Gemini provider (OpenAI-compatible endpoint).

Gemini exposes an OpenAI-compatible API at
https://generativelanguage.googleapis.com/v1beta/openai, so the client mirrors
GitHubModelsService. The free tier has per-minute and per-day quotas; when they
run out Gemini returns 429, which AIService turns into a fallback to the
configured fallback provider (Groq).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.config import Settings, get_settings
from app.database import session_scope
from app.repositories.logs_repo import LogsRepository
from app.services.groq_service import GroqService, load_prompt
from app.utils.errors import AIServiceError, ConfigurationError

logger = logging.getLogger(__name__)

GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_DEFAULT_MODEL = "gemini-3.5-flash"
GEMINI_REQUEST_TIMEOUT_SECONDS = 120.0
TEMPORARY_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def is_configured(self) -> bool:
        token = os.getenv("GEMINI_API_KEY")
        if token and token.strip():
            return True
        configured = self.settings.gemini_api_key
        return bool(configured and configured.get_secret_value().strip())

    def model_name(self) -> str:
        return (
            os.getenv("GEMINI_MODEL", self.settings.gemini_model).strip()
            or GEMINI_DEFAULT_MODEL
        )

    def _base_url(self) -> str:
        return (
            os.getenv("GEMINI_BASE_URL", self.settings.gemini_base_url).strip()
            or GEMINI_DEFAULT_BASE_URL
        )

    def _api_key(self) -> str:
        token = os.getenv("GEMINI_API_KEY")
        if token and token.strip():
            return token.strip()
        try:
            return self.settings.gemini_key()
        except ConfigurationError as exc:
            raise ConfigurationError(
                "GEMINI_API_KEY is missing. Create a key at "
                "https://aistudio.google.com/apikey."
            ) from exc

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self._base_url(),
                api_key=self._api_key(),
                timeout=GEMINI_REQUEST_TIMEOUT_SECONDS,
                # Gemini's free tier intermittently returns 503 (model
                # overloaded); the SDK retries 429/5xx with backoff.
                max_retries=2,
            )
        return self._client

    async def _record_failure(
        self,
        message: str,
        details: dict[str, Any],
    ) -> None:
        def write_log() -> None:
            try:
                with session_scope() as session:
                    LogsRepository(session).create(
                        level="ERROR",
                        module="gemini",
                        message=message,
                        details=details,
                    )
            except Exception:
                logger.exception("Could not persist Gemini integration error.")

        await asyncio.to_thread(write_log)

    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
        json_mode: bool = False,
    ) -> str:
        if not self.is_configured():
            raise ConfigurationError(
                "GEMINI_API_KEY is missing. Create a key at "
                "https://aistudio.google.com/apikey."
            )

        language = context.get("language") if isinstance(context, dict) else None
        template = load_prompt(prompt_name)
        bounded_context = GroqService._apply_prompt_budget(context)
        context_json = (
            bounded_context
            if isinstance(bounded_context, str)
            else json.dumps(bounded_context, ensure_ascii=False, default=str)
        )
        logger.info(
            (
                "gemini_payload_chars=%d source_items_used_count=%d "
                "evidence_urls_count=%d report_context_chars=%d prompt_name=%s"
            ),
            len(context_json),
            GroqService._count_source_items(bounded_context),
            GroqService._count_evidence_urls(bounded_context),
            GroqService._count_report_context_chars(bounded_context),
            prompt_name,
        )
        prompt = template.replace("{context_json}", context_json)

        request_kwargs: dict[str, Any] = {}
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}
        try:
            response = await self._get_client().chat.completions.create(
                model=self.model_name(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Follow the task exactly. Never fabricate facts, "
                            "metrics, quotes, customer evidence, or guarantees. "
                            + self.settings.user_language_instruction(language)
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **request_kwargs,
            )
            content = response.choices[0].message.content
            if not content or not str(content).strip():
                raise AIServiceError(
                    "Gemini returned an empty response.",
                    provider="gemini",
                    reason="invalid_response",
                )
            return str(content).strip()
        except ConfigurationError:
            raise
        except RateLimitError as exc:
            error = AIServiceError(
                "Gemini rate limit or quota was exceeded.",
                status=429,
                provider="gemini",
                reason="rate_limit",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except APITimeoutError as exc:
            error = AIServiceError(
                "Gemini request timed out.",
                provider="gemini",
                reason="timeout",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except APIConnectionError as exc:
            error = AIServiceError(
                "Gemini connection failed.",
                provider="gemini",
                reason="connection",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except AuthenticationError as exc:
            error = AIServiceError(
                "Gemini authentication failed. Verify GEMINI_API_KEY.",
                status=getattr(exc, "status_code", 401),
                provider="gemini",
                reason="authentication",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            reason = self._status_reason(status, str(exc))
            error = AIServiceError(
                self._status_message(status, reason),
                status=status,
                provider="gemini",
                reason=reason,
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            error = AIServiceError(
                "Gemini request timed out.",
                provider="gemini",
                reason="timeout",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (httpx.NetworkError, ConnectionError) as exc:
            error = AIServiceError(
                "Gemini connection failed.",
                provider="gemini",
                reason="connection",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            error = AIServiceError(
                "Gemini returned an invalid response.",
                provider="gemini",
                reason="invalid_response",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc

    async def _record_error(
        self,
        error: AIServiceError,
        prompt_name: str,
        exception: Exception,
    ) -> None:
        await self._record_failure(
            "Gemini generation failed.",
            {
                "exception_type": type(exception).__name__,
                "prompt_name": prompt_name,
                "status": error.status,
                "reason": error.reason,
            },
        )

    @staticmethod
    def _status_reason(status: int | None, message: str) -> str:
        normalized = message.lower()
        if status == 429 or "rate limit" in normalized or "quota" in normalized:
            return "rate_limit"
        if status in {401, 403}:
            return "authentication"
        if status in TEMPORARY_STATUS_CODES:
            return "temporary_server_error"
        return "http_error"

    @staticmethod
    def _status_message(status: int | None, reason: str) -> str:
        if reason == "rate_limit":
            return "Gemini rate limit or quota was exceeded."
        if reason == "authentication":
            return "Gemini authentication failed. Verify GEMINI_API_KEY."
        if reason == "temporary_server_error":
            return f"Gemini temporarily returned status {status}."
        return f"Gemini returned status {status or 'unknown'}."
