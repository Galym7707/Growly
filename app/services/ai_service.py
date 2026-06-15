from __future__ import annotations

import functools
import logging
from typing import Any, Protocol

from app.config import Settings, get_settings
from app.services.github_models_service import GitHubModelsService
from app.services.groq_service import GroqService
from app.utils.errors import AIServiceError, ConfigurationError

logger = logging.getLogger(__name__)

FALLBACK_STATUS_CODES = {429, 500, 502, 503, 504}
FALLBACK_REASONS = {
    "rate_limit",
    "timeout",
    "connection",
    "temporary_server_error",
}
AUTH_REASONS = {"authentication"}


class TextGenerationProvider(Protocol):
    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
    ) -> str: ...


class AIService:
    """Routes the existing AI feature interface through primary and fallback providers."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        github_models: TextGenerationProvider | None = None,
        groq: TextGenerationProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.github_models = github_models or GitHubModelsService(self.settings)
        self.groq = groq or GroqService(self.settings)
        self.last_provider_name: str | None = None
        self.last_model_name: str | None = None

    def __getattr__(self, name: str):
        wrapper = getattr(GroqService, name, None)
        if wrapper is None or not callable(wrapper):
            raise AttributeError(name)
        return functools.partial(wrapper, self)

    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
    ) -> str:
        primary_name = self._normalize_provider(
            self.settings.ai_primary_provider,
            "AI_PRIMARY_PROVIDER",
        )
        fallback_name = self._normalize_provider(
            self.settings.ai_fallback_provider,
            "AI_FALLBACK_PROVIDER",
        )
        primary = self._provider(primary_name)
        logger.info("Using primary AI provider: %s", primary_name)

        try:
            result = await primary.generate_text(
                prompt_name,
                context,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._mark_success(primary_name)
            return result
        except ConfigurationError as exc:
            return await self._fallback_or_raise(
                primary_name,
                fallback_name,
                prompt_name,
                context,
                temperature,
                max_tokens,
                exc,
                reason="configuration",
            )
        except AIServiceError as exc:
            if not self._should_fallback(exc):
                raise
            return await self._fallback_or_raise(
                primary_name,
                fallback_name,
                prompt_name,
                context,
                temperature,
                max_tokens,
                exc,
                reason=exc.reason or "temporary_error",
            )

    async def _fallback_or_raise(
        self,
        primary_name: str,
        fallback_name: str,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        temperature: float,
        max_tokens: int,
        original_error: Exception,
        *,
        reason: str,
    ) -> str:
        if fallback_name == primary_name:
            raise original_error
        if not self._provider_is_configured(fallback_name):
            if isinstance(original_error, ConfigurationError):
                raise ConfigurationError(
                    f"{original_error} The configured fallback provider "
                    f"{fallback_name!r} is not configured."
                ) from original_error
            raise original_error

        self._log_fallback(primary_name, fallback_name, reason)
        fallback = self._provider(fallback_name)
        try:
            result = await fallback.generate_text(
                prompt_name,
                context,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ConfigurationError as exc:
            raise ConfigurationError(
                f"AI fallback provider {fallback_name!r} is not configured."
            ) from exc
        self._mark_success(fallback_name)
        return result

    def _provider(self, name: str) -> TextGenerationProvider:
        if name == "github_models":
            return self.github_models
        if name == "groq":
            return self.groq
        raise ConfigurationError(
            f"Unsupported AI provider {name!r}. "
            "Use 'github_models' or 'groq'."
        )

    def _provider_is_configured(self, name: str) -> bool:
        if name == "github_models":
            service = self.github_models
            configured = getattr(service, "is_configured", None)
            if callable(configured):
                return bool(configured())
            token = self.settings.github_models_token
            return bool(token and token.get_secret_value().strip())
        if name == "groq":
            key = self.settings.groq_api_key
            return bool(
                key
                and key.get_secret_value().strip()
                and self.settings.groq_model.strip()
            )
        return False

    def _mark_success(self, provider_name: str) -> None:
        self.last_provider_name = provider_name
        self.last_model_name = self.settings.ai_model_name(provider_name)

    @staticmethod
    def _normalize_provider(value: str, env_name: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in {"github_models", "groq"}:
            raise ConfigurationError(
                f"{env_name} must be 'github_models' or 'groq'."
            )
        return normalized

    @staticmethod
    def _should_fallback(error: AIServiceError) -> bool:
        return bool(
            error.status in FALLBACK_STATUS_CODES
            or error.reason in FALLBACK_REASONS
            or error.reason in AUTH_REASONS
        )

    @staticmethod
    def _log_fallback(
        primary_name: str,
        fallback_name: str,
        reason: str,
    ) -> None:
        if (
            primary_name == "github_models"
            and fallback_name == "groq"
            and reason == "rate_limit"
        ):
            logger.warning(
                "GitHub Models failed with rate limit, falling back to Groq"
            )
            return
        if (
            primary_name == "github_models"
            and fallback_name == "groq"
            and reason == "configuration"
        ):
            logger.warning(
                "GitHub Models is not configured; falling back to Groq. "
                "Set GITHUB_MODELS_TOKEN to enable the primary provider."
            )
            return
        logger.warning(
            "AI primary provider %s failed reason=%s; falling back to %s",
            primary_name,
            reason,
            fallback_name,
        )
