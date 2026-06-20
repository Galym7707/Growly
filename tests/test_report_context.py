from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.content_plan_service import ContentPlanService
from app.web_api import ContentPlanRequest, _build_content_plan_context


def _no_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "growly_web_api_key", None)


def test_content_plan_options_are_derived_from_report_topic() -> None:
    report = SimpleNamespace(
        id=23,
        title="Анализ рынка: Логистика и доставка товаров",
        report_type="market_scan",
        query="Логистика и доставка товаров",
        summary="Краткий вывод.",
        sources_count=40,
        evidence_json=[],
        raw_json={
            "market_context": {
                "topic": "Логистика и доставка товаров",
                "region": "Казахстан",
            },
            "repeated_offers": ["Комплексная доставка по Казахстану"],
            "repeated_ctas": ["Рассчитать стоимость доставки"],
        },
    )
    context = ContentPlanService._content_plan_options_context(report, "ru")
    options = ContentPlanService._fallback_options(context, "ru")

    audiences = " ".join(option["value"] for option in options["audiences"])
    assert "Логистика и доставка товаров" in audiences
    offer_values = [option["value"] for option in options["offers"]]
    assert "Комплексная доставка по Казахстану" in offer_values
    cta_values = [option["value"] for option in options["ctas"]]
    assert "Рассчитать стоимость доставки" in cta_values
    channel_values = [option["value"] for option in options["channels"]]
    assert "telegram" in channel_values and "instagram" in channel_values
    # No unrelated hardcoded niche examples leak into the options.
    assert "прокладк" not in audiences.casefold()


def test_normalize_options_lowercases_channel_slugs() -> None:
    payload = {
        "channels": [
            {"label": "Instagram", "value": "Instagram"},
            {"label": "Telegram", "value": "Telegram"},
        ],
        "goals": [{"label": "Получить заявки", "value": "Получить больше заявок"}],
    }
    normalized = ContentPlanService._normalize_options(payload)
    assert normalized["channels"][0]["value"] == "instagram"
    assert normalized["goals"][0]["label"] == "Получить заявки"


def test_content_plan_options_endpoint(monkeypatch) -> None:
    _no_key(monkeypatch)

    async def fake_options(self, report_id, language="ru"):
        assert report_id == 23
        assert language == "ru"
        return {
            "goals": [{"label": "Получить заявки", "value": "..."}],
            "audiences": [],
            "offers": [],
            "channels": [{"label": "Telegram", "value": "telegram"}],
            "content_types": [],
            "ctas": [],
        }

    monkeypatch.setattr(
        "app.web_api.ContentPlanService.generate_content_plan_options",
        fake_options,
    )

    response = TestClient(app).post(
        "/api/reports/23/content-plan-options",
        json={"language": "ru"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["goals"][0]["label"] == "Получить заявки"
    assert body["channels"][0]["value"] == "telegram"


def test_build_content_plan_context_pins_report_and_composes_objective() -> None:
    payload = ContentPlanRequest(
        report_id=23,
        goal="Получить заявки на доставку",
        audience="владельцы интернет-магазинов",
        offer="комплексная доставка",
        channels=["telegram", "instagram"],
        cta="Оставить заявку",
        custom_instruction="без громких обещаний",
        language="ru",
    )
    context = _build_content_plan_context(payload)

    assert context["market_context"] == {"report_id": 23}
    assert context["business"]["target_audience"] == "владельцы интернет-магазинов"
    assert context["business"]["preferred_channels"] == ["telegram", "instagram"]
    objective = context["weekly_objective"]
    assert "Получить заявки на доставку" in objective
    assert "без громких обещаний" in objective


def test_chat_answers_from_selected_report(monkeypatch) -> None:
    _no_key(monkeypatch)
    captured: dict[str, object] = {}

    async def fake_answer(self, report_id, message, language="ru"):
        captured["report_id"] = report_id
        captured["message"] = message
        captured["language"] = language
        return "Ответ по отчёту."

    monkeypatch.setattr(
        "app.web_api.ReportService.answer_question",
        fake_answer,
    )

    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "Какие боли у клиентов?",
            "report_id": 23,
            "language": "ru",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "ask"
    assert body["result"]["answer"] == "Ответ по отчёту."
    assert captured["report_id"] == 23
    assert captured["message"] == "Какие боли у клиентов?"


def test_chat_ideas_action_uses_report(monkeypatch) -> None:
    _no_key(monkeypatch)

    async def fake_ideas(self, report_id, language="ru"):
        assert report_id == 23
        return "Идеи постов из отчёта:\n• Видео о доставке"

    monkeypatch.setattr("app.web_api.ReportService.report_ideas", fake_ideas)

    response = TestClient(app).post(
        "/api/chat",
        json={"message": "Показать идеи постов", "action": "ideas", "report_id": 23},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "ideas"
    assert "Видео о доставке" in body["result"]["answer"]
