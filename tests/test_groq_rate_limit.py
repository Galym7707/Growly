from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.services import groq_service
from app.services.groq_service import GroqService
from app.utils.errors import AIServiceError


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        *,
        retry_after: str | None = None,
        content: str = "completed",
    ) -> None:
        self.status_code = status_code
        self.headers = (
            {"Retry-After": retry_after} if retry_after is not None else {}
        )
        self._content = content
        self.request = httpx.Request("POST", "https://api.groq.test/chat")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "request failed",
                request=self.request,
                response=httpx.Response(
                    self.status_code,
                    request=self.request,
                ),
            )

    def json(self) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": self._content,
                    }
                }
            ]
        }


class FakeClient:
    def __init__(
        self,
        responses: Iterator[FakeResponse],
        calls: list[dict[str, Any]],
    ) -> None:
        self.responses = responses
        self.calls = calls

    async def __aenter__(self) -> FakeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return next(self.responses)


def make_service() -> GroqService:
    return GroqService(
        Settings(
            _env_file=None,
            GROQ_API_KEY="test-secret-key",
            GROQ_MODEL="test-model",
        )
    )


@pytest.mark.asyncio
async def test_groq_429_uses_retry_after_and_exponential_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            FakeResponse(429, retry_after="4"),
            FakeResponse(429),
            FakeResponse(200, content="done"),
        ]
    )
    calls: list[dict[str, Any]] = []
    delays: list[float] = []
    service = make_service()

    monkeypatch.setattr(
        groq_service.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(responses, calls),
    )

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    async def ignore_failure(message: str, details: dict[str, Any]) -> None:
        return None

    monkeypatch.setattr(groq_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(service, "_record_failure", ignore_failure)

    result = await service.generate_text("market_scan_report.md", {})

    assert result == "done"
    assert len(calls) == 3
    assert delays == [4.0, 2]


@pytest.mark.asyncio
async def test_groq_429_stops_after_three_attempts_without_exposing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter([FakeResponse(429), FakeResponse(429), FakeResponse(429)])
    calls: list[dict[str, Any]] = []
    delays: list[float] = []
    recorded: list[dict[str, Any]] = []
    service = make_service()

    monkeypatch.setattr(
        groq_service.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(responses, calls),
    )

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    async def record_failure(message: str, details: dict[str, Any]) -> None:
        recorded.append(details)

    monkeypatch.setattr(groq_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(service, "_record_failure", record_failure)

    with pytest.raises(AIServiceError) as raised:
        await service.generate_text("market_scan_report.md", {})

    assert raised.value.status == 429
    assert raised.value.is_rate_limited
    assert len(calls) == 3
    assert delays == [1, 2]
    assert "test-secret-key" not in str(raised.value)
    assert "test-secret-key" not in repr(recorded)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("responses", "expected_delays", "succeeds"),
    [
        ([FakeResponse(429, retry_after="45"), FakeResponse(200)], [45.0], True),
        ([FakeResponse(429, retry_after="3600")], [], False),
        ([FakeResponse(429, retry_after="55"), FakeResponse(429, retry_after="55")], [55.0], False),
    ],
)
async def test_groq_waits_for_minute_windows_but_bounds_total_wait(
    monkeypatch, responses, expected_delays, succeeds,
):
    calls, delays = [], []
    service = make_service()
    iterator = iter(responses)
    monkeypatch.setattr(groq_service.httpx, "AsyncClient", lambda **kw: FakeClient(iterator, calls))

    async def sleep(delay):
        delays.append(delay)

    async def record_failure(*args):
        pass

    monkeypatch.setattr(groq_service.asyncio, "sleep", sleep)
    monkeypatch.setattr(service, "_record_failure", record_failure)
    if succeeds:
        assert await service.generate_text("connection_test.md", {}) == "completed"
    else:
        with pytest.raises(AIServiceError) as error:
            await service.generate_text("connection_test.md", {})
        assert error.value.reason == "rate_limit"
        assert error.value.provider == "groq"
    assert delays == expected_delays


@pytest.mark.asyncio
@pytest.mark.parametrize("exception, reason", [
    (httpx.ConnectError("unavailable"), "connection"),
    (httpx.ReadTimeout("unavailable"), "timeout"),
])
async def test_groq_preserves_transport_failure_reason_for_provider_fallback(monkeypatch, exception, reason):
    class UnavailableClient(FakeClient):
        async def post(self, *args, **kwargs):
            raise exception

    service = make_service()
    monkeypatch.setattr(groq_service.httpx, "AsyncClient", lambda **kw: UnavailableClient(iter([]), []))

    async def noop(*args):
        pass

    monkeypatch.setattr(groq_service.asyncio, "sleep", noop)
    monkeypatch.setattr(service, "_record_failure", noop)
    with pytest.raises(AIServiceError) as error:
        await service.generate_text("connection_test.md", {})
    assert error.value.reason == reason
    assert error.value.provider == "groq"


@pytest.mark.asyncio
@pytest.mark.parametrize("model, effort", [
    ("openai/gpt-oss-120b", "low"),
    ("openai/gpt-oss-20b", "low"),
    ("test-model", None),
])
async def test_structured_summary_uses_supported_reasoning_budget(monkeypatch, model, effort):
    service = make_service()
    service.settings.groq_model = model
    calls = []
    responses = iter([FakeResponse(200, content='{"summary":"ready"}')])
    monkeypatch.setattr(groq_service.httpx, "AsyncClient", lambda **kw: FakeClient(responses, calls))
    result = await service.summarize_content_plan_sources({"source_items": []})
    assert result == '{"summary":"ready"}'
    body = calls[0]["json"]
    assert body.get("reasoning_effort") == effort
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 1400


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2])
async def test_source_batches_obey_the_provider_concurrency_limit(monkeypatch, limit):
    service = GroqService(Settings(_env_file=None, GROQ_API_KEY="test", GROQ_MAX_CONCURRENT_REQUESTS=limit))
    active = 0
    maximum = 0

    class ConcurrentClient(FakeClient):
        async def post(self, *args, **kwargs):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.01)
            active -= 1
            return FakeResponse(200)

    monkeypatch.setattr(groq_service.httpx, "AsyncClient", lambda **kw: ConcurrentClient(iter([]), []))
    result = await asyncio.gather(*(service.generate_text("connection_test.md", {}) for _ in range(4)))
    assert result == ["completed"] * 4
    assert maximum == limit
