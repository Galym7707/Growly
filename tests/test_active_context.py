from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.market_intelligence import MarketIntelligenceService
from app.web_api import _active_payload_from_report


def test_active_payload_prefers_market_context_topic() -> None:
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=23,
        title="Анализ рынка: Логистика",
        report_type="market_scan",
        query="Логистика",
        sources_count=40,
        status="ready",
        notion_page_id=None,
        created_at=now,
        raw_json={
            "market_context": {
                "topic": "Логистика и доставка товаров",
                "region": "Казахстан",
                "language": "ru",
            }
        },
    )

    payload = _active_payload_from_report(report, {})

    assert payload["report_id"] == 23
    assert payload["topic"] == "Логистика и доставка товаров"
    assert payload["region"] == "Казахстан"
    assert payload["language"] == "ru"
    assert payload["sources_count"] == 40
    assert payload["created_at"] == now.isoformat()
    assert payload["notion_synced"] is False


def test_active_payload_falls_back_to_stored_then_query() -> None:
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=9,
        title="Анализ рынка: Доставка",
        report_type="market_scan",
        query="Доставка",
        sources_count=12,
        status="ready",
        notion_page_id=None,
        created_at=now,
        raw_json={},
    )

    payload = _active_payload_from_report(report, {"active_topic": "Сохранённая тема"})

    assert payload["topic"] == "Сохранённая тема"


def test_get_active_context_returns_payload(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    monkeypatch.setattr(
        "app.web_api._active_context_data",
        lambda: {
            "active": {
                "report_id": 23,
                "topic": "Логистика и доставка товаров",
                "sources_count": 40,
            }
        },
    )

    response = TestClient(app).get("/api/context/active")

    assert response.status_code == 200
    payload = response.json()["active"]
    assert payload["report_id"] == 23
    assert payload["sources_count"] == 40


def test_get_active_context_returns_null_when_no_reports(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    monkeypatch.setattr("app.web_api._active_context_data", lambda: {"active": None})

    response = TestClient(app).get("/api/context/active")

    assert response.status_code == 200
    assert response.json()["active"] is None


def test_patch_active_context_sets_report(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    captured: dict[str, object] = {}

    def fake_set(report_id):
        captured["report_id"] = report_id
        return {"active": {"report_id": report_id, "topic": "Логистика"}}

    monkeypatch.setattr("app.web_api._set_active_context", fake_set)

    response = TestClient(app).patch(
        "/api/context/active",
        json={"active_report_id": 23},
    )

    assert response.status_code == 200
    assert captured["report_id"] == 23
    assert response.json()["active"]["report_id"] == 23


def test_market_scan_save_persists_active_context(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class FakeSettingsRepository:
        def __init__(self, session) -> None:
            del session

        def set(self, key, value):
            captured[key] = value

    monkeypatch.setattr(
        "app.services.market_intelligence.SettingsRepository",
        FakeSettingsRepository,
    )
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=23,
        query="Логистика и доставка товаров",
        report_type="market_scan",
        sources_count=40,
        created_at=now,
        raw_json={
            "market_context": {
                "topic": "Логистика и доставка товаров",
                "region": "Казахстан",
                "language": "ru",
            }
        },
    )

    MarketIntelligenceService._persist_active_context(None, report)

    assert captured["active_report_id"] == "23"
    assert captured["active_topic"] == "Логистика и доставка товаров"
    assert captured["active_region"] == "Казахстан"
    assert captured["active_language"] == "ru"
    assert captured["active_report_type"] == "market_scan"
    assert captured["active_sources_count"] == "40"
    assert captured["active_created_at"] == now.isoformat()
