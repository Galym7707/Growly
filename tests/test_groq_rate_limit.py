from __future__ import annotations

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
