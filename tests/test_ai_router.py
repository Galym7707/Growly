from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import Settings
from app.services.ai_service import AIService
from app.services.github_models_service import GitHubModelsService
from app.utils.errors import AIServiceError, ConfigurationError


class FakeProvider:
    def __init__(
        self,
        *,
        result: str = "generated",
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        prompt_name: str,
        context: dict[str, Any] | list[Any] | str,
        *,
        temperature: float = 0.35,
        max_tokens: int = 3000,
    ) -> str:
        self.calls.append(
            {
                "prompt_name": prompt_name,
                "context": context,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


class FakeGitHubClient:
    def __init__(self, content: str = "github result") -> None:
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create)
        )
        self.content = content

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content)
                )
            ]
        )


@pytest.mark.asyncio
async def test_github_models_works_when_token_is_present() -> None:
    settings = Settings(
        _env_file=None,
        GITHUB_MODELS_TOKEN="test-github-token",
        GITHUB_MODELS_MODEL="openai/gpt-5-mini",
    )
    client = FakeGitHubClient()
    service = GitHubModelsService(  # type: ignore[arg-type]
        settings,
        client=client,
    )

    result = await service.generate_text(
        "connection_test.md",
        {"check": "provider"},
        max_tokens=8,
    )

    assert result == "github result"
    assert client.requests[0]["model"] == "openai/gpt-5-mini"
    assert "test-github-token" not in repr(client.requests)


@pytest.mark.asyncio
async def test_github_429_falls_back_to_groq(
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = FakeProvider(
        error=AIServiceError(
            "rate limited",
            status=429,
            provider="github_models",
            reason="rate_limit",
        )
    )
    groq = FakeProvider(result="groq result")
    settings = Settings(
        _env_file=None,
        GITHUB_MODELS_TOKEN="test-github-token",
        GROQ_API_KEY="test-groq-token",
        GROQ_MODEL="llama-3.3-70b-versatile",
        AI_PRIMARY_PROVIDER="github_models",
        AI_FALLBACK_PROVIDER="groq",
    )
    service = AIService(  # type: ignore[arg-type]
        settings,
        github_models=github,
        groq=groq,
    )

    with caplog.at_level(logging.INFO):
        result = await service.generate_text("connection_test.md", {})

    assert result == "groq result"
    assert len(github.calls) == 1
    assert len(groq.calls) == 1
    assert service.last_provider_name == "groq"
    assert service.last_model_name == "llama-3.3-70b-versatile"
    assert "Using primary AI provider: github_models" in caplog.text
    assert (
        "GitHub Models failed with rate limit, falling back to Groq"
        in caplog.text
    )
    assert "test-github-token" not in caplog.text
    assert "test-groq-token" not in caplog.text


@pytest.mark.asyncio
async def test_missing_github_token_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    settings = Settings(
        _env_file=None,
        GITHUB_MODELS_TOKEN=None,
        GROQ_API_KEY=None,
        AI_PRIMARY_PROVIDER="github_models",
        AI_FALLBACK_PROVIDER="groq",
    )
    service = AIService(settings)

    with pytest.raises(ConfigurationError, match="GITHUB_MODELS_TOKEN"):
        await service.generate_text("connection_test.md", {})


@pytest.mark.asyncio
async def test_missing_github_token_uses_configured_groq_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    groq = FakeProvider(result="groq fallback")
    settings = Settings(
        _env_file=None,
        GITHUB_MODELS_TOKEN=None,
        GROQ_API_KEY="test-groq-token",
        AI_PRIMARY_PROVIDER="github_models",
        AI_FALLBACK_PROVIDER="groq",
    )
    service = AIService(  # type: ignore[arg-type]
        settings,
        groq=groq,
    )

    with caplog.at_level(logging.WARNING):
        result = await service.generate_text("connection_test.md", {})

    assert result == "groq fallback"
    assert "Set GITHUB_MODELS_TOKEN" in caplog.text
    assert "test-groq-token" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (404, "model_unavailable"),
        (410, "model_unavailable"),
        (500, "temporary_server_error"),
        (502, "temporary_server_error"),
        (503, "temporary_server_error"),
        (504, "temporary_server_error"),
        (None, "timeout"),
        (None, "connection"),
        (401, "authentication"),
    ],
)
async def test_temporary_github_failures_use_groq_fallback(
    status: int | None,
    reason: str,
) -> None:
    github = FakeProvider(
        error=AIServiceError(
            "temporary failure",
            status=status,
            provider="github_models",
            reason=reason,
        )
    )
    groq = FakeProvider(result="fallback")
    settings = Settings(
        _env_file=None,
        GITHUB_MODELS_TOKEN="test-github-token",
        GROQ_API_KEY="test-groq-token",
        AI_PRIMARY_PROVIDER="github_models",
        AI_FALLBACK_PROVIDER="groq",
    )
    service = AIService(  # type: ignore[arg-type]
        settings,
        github_models=github,
        groq=groq,
    )

    assert (
        await service.generate_text("connection_test.md", {})
        == "fallback"
    )


@pytest.mark.asyncio
async def test_retired_primary_and_missing_fallback_reach_working_provider():
    primary = FakeProvider(error=AIServiceError(
        "Retired model", status=410, provider="nvidia", reason="http_error",
    ))
    fallback = FakeProvider(error=AIServiceError(
        "Model missing", status=404, provider="gemini", reason="http_error",
    ))
    working = FakeProvider(result="working generation")
    settings = Settings(
        _env_file=None,
        NVIDIA_API_KEY="test-nvidia", GEMINI_API_KEY="test-gemini",
        GROQ_API_KEY="test-groq",
        AI_PRIMARY_PROVIDER="nvidia", AI_FALLBACK_PROVIDER="gemini",
    )
    service = AIService(settings, nvidia=primary, gemini=fallback, groq=working)
    assert await service.generate_text("connection_test.md", {}) == "working generation"
    assert [len(p.calls) for p in (primary, fallback, working)] == [1, 1, 1]
    assert service.last_provider_name == "groq"


@pytest.mark.asyncio
async def test_invalid_request_is_not_retried_on_other_providers():
    primary = FakeProvider(error=AIServiceError(
        "Invalid request", status=400, provider="github_models", reason="http_error",
    ))
    fallback = FakeProvider()
    settings = Settings(
        _env_file=None, GITHUB_MODELS_TOKEN="test-github", GROQ_API_KEY="test-groq",
    )
    service = AIService(settings, github_models=primary, groq=fallback)
    with pytest.raises(AIServiceError, match="Invalid request"):
        await service.generate_text("connection_test.md", {})
    assert fallback.calls == []
