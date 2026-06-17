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


def test_market_scan_response_includes_stable_report_id(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=123,
        report_type="market_scan",
        title="Market scan",
        body="Report body",
        report_text="Report body",
        summary="Summary",
        query="delivery",
        sources_count=2,
        evidence_json=[],
        recommendations_json=[],
        raw_json={},
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        created_at=now,
        updated_at=now,
    )

    async def run_market_scan(self, **kwargs):
        assert kwargs["niche"] == "delivery"
        return report, [object(), object()]

    monkeypatch.setattr(
        "app.web_api.MarketIntelligenceService.run_market_scan",
        run_market_scan,
    )

    response = TestClient(app).post(
        "/api/market-scan",
        json={
            "niche": "delivery",
            "region_language": "Kazakhstan, English",
            "competitor_keywords": "",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == 123
    assert payload["sources_count"] == 2
    assert payload["sources_saved"] == 2
    assert payload["report"]["id"] == 123


def test_content_plans_create_returns_plan_id_and_passes_language(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    now = datetime.now(UTC)
    captured: dict[str, object] = {}
    item = SimpleNamespace(
        id=45,
        publish_date=now,
        channel="Telegram",
        content_type="weekly_digest",
        topic="Market proof",
        goal="Trust",
        target_audience="Founders",
        key_message="Evidence",
        cta="Book a call",
        source_idea="Internal data",
        why_recommended="Based on latest scan",
        status="draft",
        notion_page_id=None,
        created_at=now,
        updated_at=now,
    )

    async def generate_weekly_plan(self, business_context):
        captured["context"] = business_context
        return [item]

    monkeypatch.setattr(
        "app.web_api.ContentPlanService.generate_weekly_plan",
        generate_weekly_plan,
    )

    response = TestClient(app).post(
        "/api/content-plans",
        json={
            "weekly_objective": "Build trust",
            "business": {},
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_id"] == 45
    assert payload["content_plan_id"] == 45
    assert payload["items"][0]["id"] == 45
    assert captured["context"]["language"] == "en"  # type: ignore[index]
    assert captured["context"]["business"]["language"] == "en"  # type: ignore[index]


def test_content_plans_detail_uses_real_backend_response(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    def detail(plan_id: int):
        return {
            "plan_id": plan_id,
            "items": [{"id": plan_id, "topic": "Real item"}],
            "source": {"report_id": 7, "sources_count": 42},
        }

    monkeypatch.setattr("app.web_api._content_plan_detail_response", detail)

    response = TestClient(app).get("/api/content-plans/45")

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_id"] == 45
    assert payload["items"][0]["topic"] == "Real item"
    assert payload["source"]["report_id"] == 7
