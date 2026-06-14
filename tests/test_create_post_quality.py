from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.bot.handlers import format_draft_message
from app.config import Settings
from app.services.content_types import detect_content_type
from app.services.draft_service import DraftService


class FakeGroq:
    def __init__(self, drafts: list[dict[str, Any]]) -> None:
        self.drafts = list(drafts)
        self.prompt_names: list[str] = []

    async def analyze_draft_brief(self, context: dict[str, Any]) -> str:
        return json.dumps(
            {
                "product_service": "Комплектация строительных объектов",
                "audience": "Прорабы и B2B-заказчики",
                "main_pain": "Простой из-за неполной поставки",
                "business_context": "Материалы для строительного объекта",
                "channel": "Telegram",
                "cta": "Пришлите смету на проверку",
                "allowed_claims": ["Проверка комплекта материалов"],
                "forbidden_claims": ["Гарантированная экономия"],
                "overpromising_risk": "Нельзя обещать экономию без расчёта",
            },
            ensure_ascii=False,
        )

    async def generate_content_draft(
        self, prompt_name: str, context: dict[str, Any]
    ) -> str:
        self.prompt_names.append(prompt_name)
        return json.dumps(self.drafts.pop(0), ensure_ascii=False)


def payload(text: str) -> dict[str, str]:
    return {
        "draft_text": text,
        "content_angle": "Простой объекта из-за ошибок комплектации",
        "source_insight": "Использованы только факты из brief",
        "target_pain": "Срыв сроков поставки",
        "cta": "Пришлите смету на проверку",
        "risk_check": "Экономия и сроки не гарантируются.",
        "why_this_should_work": "Ситуация знакома прорабам и ведёт к конкретному действию.",
    }


async def build_draft(
    monkeypatch: pytest.MonkeyPatch, groq: FakeGroq
) -> tuple[SimpleNamespace, dict[str, Any]]:
    service = DraftService(
        settings=Settings(_env_file=None, GROQ_MODEL="test-model"),
        groq=groq,  # type: ignore[arg-type]
    )
    saved: dict[str, Any] = {}

    async def fake_save_new(**kwargs: Any) -> SimpleNamespace:
        saved.update(kwargs)
        return SimpleNamespace(id=17, version=1, status="pending", **kwargs)

    monkeypatch.setattr(service, "_save_new", fake_save_new)
    draft = await service.create_post(
        {
            "brief": (
                "Тип контента: pain-point post\n"
                "Продукт: комплектация строительного объекта\n"
                "Аудитория: прорабы и B2B-заказчики\n"
                "Боль: простой бригады из-за неполной поставки и замены позиций\n"
                "Канал: Telegram\n"
                "CTA: Пришлите смету на проверку"
            )
        }
    )
    return draft, saved


def test_explicit_pain_point_type_is_detected() -> None:
    spec = detect_content_type("Тип контента: pain-point post\nКанал: Telegram")
    assert spec.key == "pain_point_post"
    assert spec.prompt_name == "pain_point_post.md"


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("pain-point post", "pain_point_post"),
        ("asset post", "asset_post"),
        ("case post", "case_post"),
        ("educational post", "educational_post"),
        ("comparison post", "comparison_post"),
        ("weekly digest", "weekly_digest"),
        ("Reels/Shorts script", "reels_shorts_script"),
        ("WhatsApp template", "whatsapp_template"),
    ],
)
def test_all_supported_content_types_have_stable_database_keys(
    requested: str, expected: str
) -> None:
    assert detect_content_type(f"Тип контента: {requested}").key == expected


@pytest.mark.asyncio
async def test_pain_point_brief_saves_correct_draft_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe_text = (
        "На объекте не хватает двух позиций, и бригада ждёт следующую поставку.\n\n"
        "Простой сдвигает работы, а срочная лишняя закупка усложняет смету.\n\n"
        "Проверка только общей суммы не выявляет пропуски и возможные замены позиций.\n\n"
        "Мы сверяем комплект материалов с задачами объекта и отмечаем вопросы.\n\n"
        "Пришлите смету на проверку"
    )
    groq = FakeGroq([payload(safe_text)])
    draft, saved = await build_draft(monkeypatch, groq)

    assert draft.draft_type == "pain_point_post"
    assert saved["prompt_name"] == "pain_point_post.md"
    assert groq.prompt_names == ["pain_point_post.md"]
    assert "Пришлите смету на проверку" in draft.draft_text


@pytest.mark.asyncio
async def test_forbidden_claim_is_revised_before_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsafe = payload(
        "Гарантированная экономия для каждого объекта.\n"
        "Пришлите смету на проверку"
    )
    safe = payload(
        "Неполный комплект материалов может остановить бригаду на объекте.\n"
        "Пришлите смету на проверку"
    )
    groq = FakeGroq([unsafe, safe])
    draft, _ = await build_draft(monkeypatch, groq)

    assert len(groq.prompt_names) == 2
    assert "гарантированная экономия" not in draft.draft_text.lower()
    assert "Пришлите смету на проверку" in draft.draft_text


def test_telegram_draft_includes_type_why_and_risk() -> None:
    draft = SimpleNamespace(
        id=17,
        version=2,
        status="pending",
        draft_type="pain_point_post",
        title="Простой на объекте",
        draft_text="Текст черновика\nCTA",
        generation_metadata_json={
            "why_this_should_work": "Конкретная ситуация узнаваема для прораба.",
            "risk_check": "Нет неподтверждённых обещаний.",
        },
    )

    rendered = format_draft_message(draft)

    assert "Черновик #17 · версия 2 · статус ожидает согласования" in rendered
    assert "Тип контента: Пост о проблеме клиента" in rendered
    assert "Почему этот пост" in rendered
    assert "Проверка рисков" in rendered
