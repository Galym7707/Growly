from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.bot.handlers import format_draft_message
from app.config import Settings
from app.services.content_types import detect_content_type
from app.services.draft_service import DraftService
from app.utils.errors import AIServiceError


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


class _Groq:
    """Fake AI returning a fixed analysis CTA and a fixed draft each call."""

    def __init__(self, analyze_cta: str, draft: dict[str, Any]) -> None:
        self.analyze_cta = analyze_cta
        self.draft = draft
        self.calls = 0

    async def analyze_draft_brief(self, context: dict[str, Any]) -> str:
        return json.dumps(
            {
                "product_service": "Логистика и доставка",
                "audience": "B2B-заказчики",
                "main_pain": "Срыв сроков поставки",
                "business_context": "Доставка товаров по Казахстану",
                "channel": "Telegram",
                "cta": self.analyze_cta,
                "allowed_claims": ["Отслеживание заказов"],
                "forbidden_claims": ["Гарантированная экономия"],
                "overpromising_risk": "Нельзя обещать экономию без расчёта",
            },
            ensure_ascii=False,
        )

    async def generate_content_draft(
        self, prompt_name: str, context: dict[str, Any]
    ) -> str:
        del prompt_name, context
        self.calls += 1
        return json.dumps(self.draft, ensure_ascii=False)


async def _run(monkeypatch: pytest.MonkeyPatch, groq: _Groq, brief: str) -> Any:
    service = DraftService(
        settings=Settings(_env_file=None, GROQ_MODEL="test-model"),
        groq=groq,  # type: ignore[arg-type]
    )

    async def fake_save_new(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(id=1, version=1, status="pending", **kwargs)

    monkeypatch.setattr(service, "_save_new", fake_save_new)
    return await service.create_post({"brief": brief})


@pytest.mark.asyncio
async def test_create_post_without_explicit_cta_does_not_require_inferred_cta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No "CTA:" line in the brief (the "create post from latest analysis" flow).
    draft = payload(
        "Неполная поставка останавливает работу на объекте и сдвигает сроки.\n\n"
        "Мы сверяем комплект и показываем статус каждого заказа.\n\n"
        "Напишите нам, чтобы обсудить вашу задачу."
    )
    groq = _Groq(analyze_cta="Пришлите смету на проверку", draft=draft)
    result = await _run(
        monkeypatch,
        groq,
        "Создай продающий пост для канала Telegram на основе последнего анализа. "
        "Ниша: Логистика и доставка товаров. Добавь конкретный призыв к действию.",
    )
    # The draft does not echo the inferred CTA verbatim, yet it is accepted on
    # the first attempt instead of being rejected.
    assert groq.calls == 1
    assert "Напишите нам" in result.draft_text


@pytest.mark.asyncio
async def test_persistent_unsafe_draft_raises_friendly_russian_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = payload("Гарантированная экономия для каждого объекта.\n\nНапишите нам.")
    groq = _Groq(analyze_cta="Напишите нам", draft=draft)
    with pytest.raises(AIServiceError, match="Не удалось подготовить безопасный текст поста"):
        await _run(monkeypatch, groq, "Создай пост. Ниша: Логистика.")
    assert groq.calls == 3


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
