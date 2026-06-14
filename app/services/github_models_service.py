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

GITHUB_MODELS_DEFAULT_BASE_URL = "https://models.github.ai/inference"
GITHUB_MODELS_DEFAULT_MODEL = "openai/gpt-5-mini"
GITHUB_MODELS_REQUEST_TIMEOUT_SECONDS = 60.0
TEMPORARY_STATUS_CODES = {429, 500, 502, 503, 504}


class GitHubModelsService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def is_configured(self) -> bool:
        token = os.getenv("GITHUB_MODELS_TOKEN")
        if token and token.strip():
            return True
        configured = self.settings.github_models_token
        return bool(
            configured
            and configured.get_secret_value().strip()
        )

    def model_name(self) -> str:
        return (
            os.getenv(
                "GITHUB_MODELS_MODEL",
                self.settings.github_models_model,
            ).strip()
            or GITHUB_MODELS_DEFAULT_MODEL
        )

    def _base_url(self) -> str:
        return (
            os.getenv(
                "GITHUB_MODELS_BASE_URL",
                self.settings.github_models_base_url,
            ).strip()
            or GITHUB_MODELS_DEFAULT_BASE_URL
        )

    def _api_key(self) -> str:
        token = os.getenv("GITHUB_MODELS_TOKEN")
        if token and token.strip():
            return token.strip()
        try:
            return self.settings.github_models_key()
        except ConfigurationError as exc:
            raise ConfigurationError(
                "GITHUB_MODELS_TOKEN is missing. Configure a GitHub token "
                "with models:read permission."
            ) from exc

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self._base_url(),
                api_key=self._api_key(),
                timeout=GITHUB_MODELS_REQUEST_TIMEOUT_SECONDS,
                max_retries=0,
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
                        module="github_models",
                        message=message,
                        details=details,
                    )
            except Exception:
                logger.exception(
                    "Could not persist GitHub Models integration error."
                )

        await asyncio.to_thread(write_log)

    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
    ) -> str:
        if not self.is_configured():
            raise ConfigurationError(
                "GITHUB_MODELS_TOKEN is missing. Configure a GitHub token "
                "with models:read permission."
            )

        template = load_prompt(prompt_name)
        bounded_context = GroqService._apply_prompt_budget(context)
        context_json = (
            bounded_context
            if isinstance(bounded_context, str)
            else json.dumps(
                bounded_context,
                ensure_ascii=False,
                default=str,
            )
        )
        logger.info(
            (
                "github_models_payload_chars=%d source_items_used_count=%d "
                "evidence_urls_count=%d report_context_chars=%d prompt_name=%s"
            ),
            len(context_json),
            GroqService._count_source_items(bounded_context),
            GroqService._count_evidence_urls(bounded_context),
            GroqService._count_report_context_chars(bounded_context),
            prompt_name,
        )
        prompt = template.replace("{context_json}", context_json)

        try:
            response = await self._get_client().chat.completions.create(
                model=self.model_name(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Follow the task exactly. Never fabricate facts, "
                            "metrics, quotes, customer evidence, or guarantees."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if not content or not str(content).strip():
                raise AIServiceError(
                    "GitHub Models returned an empty response.",
                    provider="github_models",
                    reason="invalid_response",
                )
            return str(content).strip()
        except ConfigurationError:
            raise
        except RateLimitError as exc:
            error = AIServiceError(
                "GitHub Models rate limit or quota was exceeded.",
                status=429,
                provider="github_models",
                reason="rate_limit",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except APITimeoutError as exc:
            error = AIServiceError(
                "GitHub Models request timed out.",
                provider="github_models",
                reason="timeout",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except APIConnectionError as exc:
            error = AIServiceError(
                "GitHub Models connection failed.",
                provider="github_models",
                reason="connection",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except AuthenticationError as exc:
            error = AIServiceError(
                "GitHub Models authentication failed. Verify "
                "GITHUB_MODELS_TOKEN and its models:read permission.",
                status=getattr(exc, "status_code", 401),
                provider="github_models",
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
                provider="github_models",
                reason=reason,
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            error = AIServiceError(
                "GitHub Models request timed out.",
                provider="github_models",
                reason="timeout",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (httpx.NetworkError, ConnectionError) as exc:
            error = AIServiceError(
                "GitHub Models connection failed.",
                provider="github_models",
                reason="connection",
            )
            await self._record_error(error, prompt_name, exc)
            raise error from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            error = AIServiceError(
                "GitHub Models returned an invalid response.",
                provider="github_models",
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
            "GitHub Models generation failed.",
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
            return "GitHub Models rate limit or quota was exceeded."
        if reason == "authentication":
            return (
                "GitHub Models authentication failed. Verify "
                "GITHUB_MODELS_TOKEN and its models:read permission."
            )
        if reason == "temporary_server_error":
            return f"GitHub Models temporarily returned status {status}."
        return f"GitHub Models returned status {status or 'unknown'}."
