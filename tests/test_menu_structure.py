from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ConversationHandler

from app.bot import handlers
from app.bot.keyboards import (
    competitor_report_actions_keyboard,
    create_post_menu_keyboard,
    empty_performance_actions_keyboard,
    main_menu_keyboard,
    more_menu_keyboard,
    reports_menu_keyboard,
    settings_menu_keyboard,
    sources_menu_keyboard,
)
from app.bot.states import BotState
from app.services.content_types import normalize_content_type


def keyboard_labels(markup: object) -> list[list[str]]:
    return [
        [button.text for button in row]
        for row in markup.keyboard  # type: ignore[attr-defined]
    ]


def test_main_menu_contains_only_primary_workflows() -> None:
    assert keyboard_labels(main_menu_keyboard()) == [
        ["Анализ рынка", "Контент-план"],
        ["Создать пост", "Источники"],
        ["Черновики", "Отчёты"],
        ["Ещё"],
    ]


def test_submenus_match_mvp_structure() -> None:
    assert keyboard_labels(sources_menu_keyboard()) == [
        ["Просмотреть источники"],
        ["Найти новые источники", "Проверить источники"],
        ["Назад"],
    ]
    assert keyboard_labels(create_post_menu_keyboard()) == [
        ["Рекламный пост", "Обучающий пост"],
        ["Пост о результате клиента", "FAQ-пост"],
        ["Новостной пост", "Instagram caption"],
        ["Свой вариант"],
        ["Назад"],
    ]
    assert keyboard_labels(reports_menu_keyboard()) == [
        ["Последний анализ рынка"],
        ["Последний конкурентный отчёт"],
        ["Отчёт по публикациям"],
        ["Все отчёты"],
        ["Назад"],
    ]
    assert keyboard_labels(settings_menu_keyboard()) == [
        ["Показать настройки", "Новый бизнес"],
        ["Сохранить в Notion"],
        ["Язык"],
        ["Назад"],
    ]
    assert keyboard_labels(more_menu_keyboard()) == [
        ["Веб-поиск", "Анализ отзывов"],
        ["Настройки", "Справка"],
        ["Назад"],
    ]


def test_competitor_report_actions_are_concise_follow_ups() -> None:
    keyboard = competitor_report_actions_keyboard(42)
    buttons = {
        button.text: button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    }
    assert buttons == {
        "Открыть полный отчёт": "report:view:42",
        "Контент-план": "report:content_plan:42",
        "Создать пост": "report:create_post:42",
        "Сохранить в Notion": "report:notion:42",
    }


@pytest.mark.asyncio
async def test_competitor_report_telegram_message_is_a_short_summary() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    report = SimpleNamespace(
        id=42,
        summary="Краткий вывод",
        sources_count=18,
        raw_json={
            "executive_summary": "Конкуренты делают упор на аудит.",
            "competitors": [
                {
                    "competitor": "Alpha",
                    "channel": "Instagram",
                    "offer": "Пробный аудит",
                    "strengths": "Ясный оффер",
                    "weaknesses": "Мало кейсов",
                    "opportunity": "Показать результаты клиентов",
                }
            ],
            "actions_this_week": [
                "Опубликовать один результат клиента",
                "Сравнить форматы офферов",
                "Уточнить CTA",
                "Собрать FAQ",
                "Запустить пробное предложение",
            ],
        },
    )

    await handlers.send_competitor_report_summary(bot, 123, report)

    text = bot.send_message.await_args.args[1]
    assert len(text) < 2000
    assert "Конкурентный отчёт сохранён." in text
    assert "Главный вывод:" in text
    assert "Конкуренты:" in text
    assert "Канал: Instagram" in text
    assert "Оффер: Пробный аудит" in text
    assert "Сильная сторона: Ясный оффер" in text
    assert "Слабая сторона: Мало кейсов" in text
    assert "Возможность: Показать результаты клиентов" in text
    assert "5 действий на эту неделю:" in text
    assert "Проверено источников: 18" in text
    assert "Alpha" in text


@pytest.mark.asyncio
async def test_long_competitor_report_sends_only_compact_telegram_summary() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    report = SimpleNamespace(
        id=42,
        summary="Краткий вывод",
        sources_count=25,
        raw_json={
            "executive_summary": "Вывод " * 300,
            "competitors": [
                {
                    "competitor": f"Конкурент {index}",
                    "channel": "Instagram и Telegram " * 20,
                    "offer": "Подробное предложение " * 20,
                    "strengths": "Сильная сторона " * 20,
                    "weaknesses": "Слабая сторона " * 20,
                    "opportunity": "Возможность " * 20,
                }
                for index in range(1, 6)
            ],
            "actions_this_week": [f"Действие {index} " * 30 for index in range(1, 6)],
        },
    )

    await handlers.send_competitor_report_summary(bot, 123, report)

    text = bot.send_message.await_args.args[1]
    assert len(text) < 4096
    assert "Полная версия доступна по кнопке." in text
    assert "Проверено источников: 25" in text


def test_empty_performance_actions_are_in_russian() -> None:
    keyboard = empty_performance_actions_keyboard()
    assert [button.text for row in keyboard.inline_keyboard for button in row] == [
        "Контент-план",
        "Создать пост",
        "Открыть черновики",
    ]


@pytest.mark.asyncio
async def test_content_plan_questions_are_clear_and_russian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(text="", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=None,
        effective_chat=None,
    )
    context = SimpleNamespace(user_data={})

    class FakeContentPlanService:
        async def latest_market_context(
            self,
            user_id: int | None = None,
        ) -> dict[str, object]:
            assert user_id is None
            return {
                "topic": "ПП-рационы в Алматы",
                "region": "Алматы",
                "language": "ru",
                "category": "доставка здорового и правильного питания",
                "category_code": "healthy_food_delivery",
                "report_id": 77,
                "source_item_ids": [1, 2],
            }

        async def intelligence_status(self) -> dict[str, bool]:
            return {"market_scan": True}

    monkeypatch.setattr(
        handlers,
        "ContentPlanService",
        FakeContentPlanService,
    )

    state = await handlers.content_plan_start(update, context)
    assert state == BotState.PLAN_GOAL
    goal_question = message.reply_text.await_args.args[0]
    assert "Какая главная цель контента на эту неделю?" in goal_question
    assert "Получить больше заявок" in goal_question
    assert "leads" not in goal_question

    message.text = "2"
    state = await handlers.content_plan_goal(update, context)
    assert state == BotState.PLAN_AUDIENCE
    audience_question = message.reply_text.await_args.args[0]
    assert "Кто главная аудитория?" in audience_question
    assert "Владельцы малого бизнеса" in audience_question
    assert context.user_data["plan_brief"]["goal"] == "Повысить доверие"

    message.text = "4"
    state = await handlers.content_plan_audience(update, context)
    assert state == BotState.PLAN_OFFER
    offer_question = message.reply_text.await_args.args[0]
    assert "Какой продукт, услугу или оффер" in offer_question
    assert "Рацион правильного питания на 7 дней с доставкой по Алматы" in (
        offer_question
    )
    assert "Пробный день ПП-питания со скидкой" in offer_question
    assert "проклад" not in offer_question.casefold()
    assert context.user_data["plan_brief"]["audience"] == "B2B-клиенты"
    assert context.user_data["plan_brief"]["market_context"]["report_id"] == 77


@pytest.mark.asyncio
async def test_content_plan_without_market_context_uses_neutral_example() -> None:
    message = SimpleNamespace(text="Своя аудитория", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(
        user_data={
            "plan_brief": {
                "market_context": None,
                "use_market_context": False,
            }
        }
    )

    state = await handlers.content_plan_audience(update, context)

    assert state == BotState.PLAN_OFFER
    offer_question = message.reply_text.await_args.args[0]
    assert (
        "Например: консультация, услуга, набор товаров, пробный тариф "
        "или акция недели."
    ) in offer_question
    assert "проклад" not in offer_question.casefold()


@pytest.mark.asyncio
async def test_content_plan_checks_for_a_new_market_topic_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(text="обычная", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=123),
        effective_user=None,
    )
    context = SimpleNamespace(
        user_data={
            "plan_brief": {
                "market_context": {
                    "topic": "B2B-автоматизация",
                    "report_id": 10,
                }
            }
        }
    )

    class FakeContentPlanService:
        async def latest_market_context(
            self,
            user_id: int | None = None,
        ) -> dict[str, object]:
            assert user_id is None
            return {
                "topic": "ПП-рационы в Алматы",
                "report_id": 11,
            }

    monkeypatch.setattr(
        handlers,
        "ContentPlanService",
        FakeContentPlanService,
    )

    state = await handlers.content_plan_finish(update, context)

    assert state == BotState.PLAN_CONTEXT_GUARD
    prompt = message.reply_text.await_args.args[0]
    assert (
        prompt
        == "Использовать последний анализ рынка: ПП-рационы в Алматы? "
        "Да / Нет / Указать другую нишу"
    )


@pytest.mark.asyncio
async def test_report_button_cannot_bypass_market_context_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        data="market:content_plan:10",
        answer=AsyncMock(),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_message=message,
        effective_chat=SimpleNamespace(id=123),
        effective_user=None,
    )
    context = SimpleNamespace(
        user_data={},
        bot=SimpleNamespace(send_message=AsyncMock()),
    )

    class FakeContentPlanService:
        async def market_context_for_report(
            self,
            report_id: int,
        ) -> dict[str, object]:
            assert report_id == 10
            return {"topic": "B2B-автоматизация", "report_id": 10}

        async def latest_market_context(
            self,
            user_id: int | None = None,
        ) -> dict[str, object]:
            assert user_id is None
            return {"topic": "ПП-рационы в Алматы", "report_id": 11}

    monkeypatch.setattr(
        handlers,
        "ContentPlanService",
        FakeContentPlanService,
    )

    state = await handlers.contextual_content_plan_start(update, context)

    assert state == BotState.PLAN_CONTEXT_GUARD
    assert context.user_data["context_guard_resume"] == "goal"
    assert "ПП-рационы в Алматы" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_empty_performance_report_is_short_and_russian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=123),
    )
    context = SimpleNamespace(bot=SimpleNamespace())

    class FakeReportService:
        async def generate_weekly_performance_report(self) -> None:
            return None

    monkeypatch.setattr(handlers, "ReportService", FakeReportService)

    await handlers.performance_report(update, context)

    final_text = message.reply_text.await_args_list[-1].args[0]
    assert "Пока нет данных для отчёта." in final_text
    assert "опубликованных постов или метрик" in final_text
    assert len(final_text) < 500
    for forbidden in (
        "Weekly Report",
        "Number of drafts",
        "Approved drafts",
        "Published items",
        "Not applicable",
    ):
        assert forbidden not in final_text


@pytest.mark.parametrize(
    ("label", "key", "prompt_name"),
    [
        ("Рекламный пост", "promo_post", "promo_post.md"),
        ("Обучающий пост", "educational_post", "educational_post.md"),
        ("Пост о результате клиента", "case_post", "case_post.md"),
        ("FAQ-пост", "faq_post", "faq_post.md"),
        ("Новостной пост", "news_post", "news_post.md"),
    ],
)
def test_post_menu_types_resolve_to_real_prompts(
    label: str,
    key: str,
    prompt_name: str,
) -> None:
    spec = normalize_content_type(label)
    assert spec.key == key
    assert spec.prompt_name == prompt_name


@pytest.mark.asyncio
async def test_selected_post_type_is_added_to_generation_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        text="FAQ-пост",
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(user_data={})

    state = await handlers.create_post_type_start(update, context)

    assert state == BotState.WAITING_POST
    assert context.user_data["post_type"] == "faq_post"

    captured: dict[str, object] = {}

    class FakeDraftService:
        async def create_post(self, payload: dict[str, object]) -> object:
            captured.update(payload)
            return SimpleNamespace(id=1)

    async def ignore_send_draft(*args: object) -> None:
        return None

    monkeypatch.setattr(handlers, "DraftService", FakeDraftService)
    monkeypatch.setattr(handlers, "send_draft", ignore_send_draft)
    message.text = "Вопросы клиентов и подтверждённые ответы."

    result = await handlers.create_post_finish(update, context)

    assert result == ConversationHandler.END
    assert str(captured["brief"]).startswith("Content type: faq_post\n")
    assert "post_type" not in context.user_data
