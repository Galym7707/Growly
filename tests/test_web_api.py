from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.utils.errors import AIServiceError


def test_root_health_is_available_for_container_readiness() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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

    async def list_latest_summary(self, limit: int = 10, workspace_id=None):
        assert workspace_id is None
        assert limit == 50
        return [report]

    monkeypatch.setattr(
        "app.web_api.ReportService.list_latest_summary",
        list_latest_summary,
    )

    response = TestClient(app).get("/api/reports")

    assert response.status_code == 200
    payload = response.json()["items"][0]
    assert payload["id"] == 7
    assert payload["body"] is None
    assert payload["structure"] == {}


def test_report_endpoint_returns_requested_translation(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    now = datetime.now(UTC)
    source = SimpleNamespace(
        id=7,
        report_type="market_scan",
        title="РђРЅР°Р»РёР· СЂС‹РЅРєР°",
        body="РўРµРєСЃС‚",
        report_text="РўРµРєСЃС‚",
        summary="РљСЂР°С‚РєРёР№ РІС‹РІРѕРґ",
        query="СЂС‹РЅРѕРє",
        sources_count=3,
        evidence_json=["https://example.com"],
        recommendations_json=[],
        raw_json={"audience_pains": ["РќРµС‚ РІСЂРµРјРµРЅРё"]},
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        workspace_id=None,
        created_at=now,
        updated_at=now,
    )
    translated = SimpleNamespace(
        **{
            **source.__dict__,
            "summary": "Short conclusion",
            "body": "Translated body",
            "report_text": "Translated body",
            "raw_json": {"audience_pains": ["No time"]},
        }
    )
    captured: dict[str, str] = {}

    async def get_report(self, report_id: int):
        assert report_id == 7
        return source

    async def localized_report(self, report, language: str):
        assert report is source
        captured["language"] = language
        return translated

    monkeypatch.setattr("app.web_api.ReportService.get_report", get_report)
    monkeypatch.setattr("app.web_api.ReportService.localized_report", localized_report)

    response = TestClient(app).get("/api/reports/7?language=en")

    assert response.status_code == 200
    payload = response.json()["report"]
    assert captured == {"language": "en"}
    assert payload["summary"] == "Short conclusion"
    assert payload["body"] == "Translated body"
    assert payload["structure"]["audience_pains"] == ["No time"]


def test_market_scan_starts_background_job_without_waiting(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    job = SimpleNamespace(
        id=77,
        current_step="Шаг 1/5: ищу источники через Tavily...",
        sources_count=0,
    )
    scheduled: dict[str, object] = {}

    async def create_market_scan_job(self, user_id, query):
        assert user_id is None
        assert query == "delivery"
        return job

    def schedule(service, job_id, payload):
        scheduled.update(
            service=service,
            job_id=job_id,
            niche=payload.niche,
        )

    monkeypatch.setattr(
        "app.web_api.MarketIntelligenceService.create_market_scan_job",
        create_market_scan_job,
    )
    monkeypatch.setattr("app.web_api._schedule_market_scan_job", schedule)

    response = TestClient(app).post(
        "/api/market-scan",
        json={
            "niche": "delivery",
            "region_language": "Kazakhstan, English",
            "competitor_keywords": "",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload == {
        "status": "accepted",
        "message": "Анализ рынка запущен",
        "job_id": 77,
        "current_step": "Шаг 1/5: ищу источники через Tavily...",
        "sources_count": 0,
    }
    assert scheduled["job_id"] == 77
    assert scheduled["niche"] == "delivery"


def test_market_scan_job_status_includes_stable_report_id(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    async def market_scan_job(self, job_id):
        assert job_id == 77
        return {
            "id": 77,
            "status": "completed",
            "current_step": "Готово.",
            "sources_count": 42,
            "report_id": 123,
            "report_status": "ready",
            "error_message": None,
        }

    monkeypatch.setattr(
        "app.web_api.MarketIntelligenceService.market_scan_job",
        market_scan_job,
    )

    response = TestClient(app).get("/api/market-scan/jobs/77")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["report_id"] == 123
    assert payload["sources_count"] == 42
    assert payload["sources_saved"] == 42


def test_chat_competitors_uses_resolved_membership_for_internal_call(
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=88,
        report_type="competitor_report",
        title="Конкурентный отчёт: финансы",
        body="Текст",
        report_text="Текст",
        summary="Краткий вывод",
        query="финансы",
        sources_count=3,
        evidence_json=[],
        recommendations_json=[],
        raw_json={},
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        workspace_id=None,
        created_at=now,
        updated_at=now,
    )

    async def generate_competitor_report(
        self,
        *,
        query=None,
        market_report_id=None,
        output_language=None,
    ):
        del self, market_report_id
        assert query == "финансы"
        assert output_language == "ru"
        return report

    monkeypatch.setattr(
        "app.web_api.MarketIntelligenceService.generate_competitor_report",
        generate_competitor_report,
    )

    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "финансы",
            "action": "competitors",
            "context": {"query": "финансы"},
            "language": "ru",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["report_id"] == 88


def test_chat_returns_clear_message_for_ai_rate_limit(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    async def generate_competitor_report(self, **kwargs):
        del self, kwargs
        raise AIServiceError(
            "rate limited",
            status=429,
            provider="github_models",
            reason="rate_limit",
        )

    monkeypatch.setattr(
        "app.web_api.MarketIntelligenceService.generate_competitor_report",
        generate_competitor_report,
    )

    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "финансы",
            "action": "competitors",
            "context": {"query": "финансы"},
            "language": "ru",
        },
    )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Генерация временно недоступна: лимит AI-сервиса исчерпан. "
        "Попробуйте позже."
    )


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


def test_content_plan_source_is_not_inferred_from_latest_report() -> None:
    from app.web_api import _content_plan_source_payload

    class FakeSession:
        pass

    assert _content_plan_source_payload(FakeSession()) is None


def test_content_plan_list_and_detail_keep_the_latest_batch_together(
    monkeypatch,
) -> None:
    from app.web_api import (
        _content_plan_detail_response,
        _list_content_plan_response,
    )

    created_at = datetime.now(UTC)
    first = SimpleNamespace(id=21, created_at=created_at)
    last = SimpleNamespace(id=22, created_at=created_at)

    class FakeSession:
        def scalar(self, statement):
            del statement
            return last

        def scalars(self, statement):
            del statement
            return [first, last]

        def get(self, model, item_id):
            del model, item_id
            return last

    @contextmanager
    def fake_session_scope():
        yield FakeSession()

    monkeypatch.setattr("app.web_api.session_scope", fake_session_scope)
    monkeypatch.setattr(
        "app.web_api._content_plan_payload",
        lambda item: {"id": item.id},
    )
    monkeypatch.setattr(
        "app.web_api._content_plan_source_payload",
        lambda session: None,
    )

    latest = _list_content_plan_response(40)
    detail = _content_plan_detail_response(22)

    assert latest["plan_id"] == 21
    assert latest["content_plan_id"] == 21
    assert [item["id"] for item in latest["items"]] == [21, 22]
    assert detail["plan_id"] == 21
    assert [item["id"] for item in detail["items"]] == [21, 22]
