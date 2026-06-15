from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_web_health_is_available_without_key_when_unconfigured(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_web_api_rejects_invalid_configured_key(monkeypatch) -> None:
    from pydantic import SecretStr

    settings = get_settings()
    monkeypatch.setattr(
        settings,
        "growly_web_api_key",
        SecretStr("server-only-key"),
    )

    response = TestClient(app).get(
        "/api/health",
        headers={"X-Growly-API-Key": "wrong"},
    )

    assert response.status_code == 401


def test_reports_endpoint_serializes_structured_report(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=7,
        report_type="competitor_report",
        title="Конкуренты",
        body="Текст",
        report_text="Текст",
        summary="Краткий вывод",
        query="рынок",
        sources_count=3,
        evidence_json=["https://example.com"],
        recommendations_json=["Проверить оффер"],
        raw_json={"competitors": [{"competitor": "Example"}]},
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        created_at=now,
        updated_at=now,
    )

    async def list_latest(self, limit: int = 10):
        assert limit == 50
        return [report]

    monkeypatch.setattr(
        "app.web_api.ReportService.list_latest",
        list_latest,
    )

    response = TestClient(app).get("/api/reports")

    assert response.status_code == 200
    payload = response.json()["items"][0]
    assert payload["id"] == 7
    assert payload["structure"]["competitors"][0]["competitor"] == "Example"
