from __future__ import annotations

import asyncio
import logging
from contextvars import ContextVar
from typing import Any

from app.database import session_scope
from app.repositories.settings_repo import SettingsRepository

SUPPORTED_LANGUAGES = ("ru", "en", "kk")
DEFAULT_LANGUAGE = "ru"
logger = logging.getLogger(__name__)

_current_language: ContextVar[str] = ContextVar(
    "telegram_language",
    default=DEFAULT_LANGUAGE,
)

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "Анализ рынка": "Market analysis",
        "Контент-план": "Content plan",
        "Создать пост": "Create post",
        "Источники": "Sources",
        "Черновики": "Drafts",
        "Отчёты": "Reports",
        "Ещё": "More",
        "Просмотреть источники": "View sources",
        "Найти новые источники": "Find new sources",
        "Проверить источники": "Check sources",
        "Назад": "Back",
        "Рекламный пост": "Promo post",
        "Обучающий пост": "Educational post",
        "Пост о результате клиента": "Client result post",
        "FAQ-пост": "FAQ post",
        "Новостной пост": "News post",
        "Свой вариант": "Custom post",
        "Последний анализ рынка": "Latest market analysis",
        "Последний конкурентный отчёт": "Latest competitor report",
        "Отчёт по публикациям": "Publication report",
        "Все отчёты": "All reports",
        "Показать настройки": "View settings",
        "Новый бизнес": "New business",
        "Синхронизировать с Notion": "Sync with Notion",
        "Язык": "Language",
        "Веб-поиск": "Web search",
        "Анализ отзывов": "Review analysis",
        "Настройки": "Settings",
        "Справка": "Help",
        "Подтвердить #{id}": "Approve #{id}",
        "Отключить #{id}": "Disable #{id}",
        "Конкуренты": "Competitors",
        "Новый поиск": "New search",
        "Открыть полный отчёт": "Open full report",
        "Создать контент-план": "Create content plan",
        "Создать пост по отчёту": "Create post from report",
        "Пост о результате": "Client result post",
        "Повторить ИИ-анализ": "Retry AI analysis",
        "Открыть источники": "Open sources",
        "Создать план по доступным данным": "Create plan from available data",
        "Да, удалить контекст": "Yes, delete context",
        "Отмена": "Cancel",
        "Одобрить": "Approve",
        "Создать заново": "Regenerate",
        "Редактировать": "Edit",
        "Отклонить": "Reject",
        "Сохранить в Notion": "Save to Notion",
        "Опубликовать в Telegram": "Publish to Telegram",
        "Запланировать": "Schedule",
        "Открыть черновики": "Open drafts",
        "Главное меню:": "Main menu:",
        "Выберите действие:": "Choose an action:",
        "Выберите тип поста:": "Choose a post type:",
        "Настройки:": "Settings:",
        "Источники:": "Sources:",
        "Ещё:": "More:",
        "Отчёты\n\nВыберите, что открыть:": "Reports\n\nChoose what to open:",
        "Язык интерфейса:": "Interface language:",
        "Язык изменён на English.": "Language changed to English.",
        "Эта кнопка устарела. Откройте /start и выберите действие заново.":
            "This button is outdated. Open /start and choose an action again.",
        "Growly управляет источниками, рыночной аналитикой, контент-планами, ИИ-черновиками и согласованием через Telegram и Notion.":
            "Growly manages sources, market intelligence, content plans, AI drafts, and approvals through Telegram and Notion.",
    },
    "kk": {
        "Анализ рынка": "Нарықты талдау",
        "Контент-план": "Контент-жоспар",
        "Создать пост": "Жазба жасау",
        "Источники": "Дереккөздер",
        "Черновики": "Нобайлар",
        "Отчёты": "Есептер",
        "Ещё": "Қосымша",
        "Просмотреть источники": "Дереккөздерді көру",
        "Найти новые источники": "Жаңа дереккөздерді табу",
        "Проверить источники": "Дереккөздерді тексеру",
        "Назад": "Артқа",
        "Рекламный пост": "Жарнамалық жазба",
        "Обучающий пост": "Оқыту жазбасы",
        "Пост о результате клиента": "Клиент нәтижесі туралы жазба",
        "FAQ-пост": "FAQ жазбасы",
        "Новостной пост": "Жаңалық жазбасы",
        "Свой вариант": "Өз нұсқаңыз",
        "Последний анализ рынка": "Соңғы нарық талдауы",
        "Последний конкурентный отчёт": "Соңғы бәсекелестер есебі",
        "Отчёт по публикациям": "Жарияланымдар есебі",
        "Все отчёты": "Барлық есептер",
        "Показать настройки": "Баптауларды көрсету",
        "Новый бизнес": "Жаңа бизнес",
        "Синхронизировать с Notion": "Notion-мен синхрондау",
        "Язык": "Тіл",
        "Веб-поиск": "Веб-іздеу",
        "Анализ отзывов": "Пікірлерді талдау",
        "Настройки": "Баптаулар",
        "Справка": "Анықтама",
        "Подтвердить #{id}": "#{id} растау",
        "Отключить #{id}": "#{id} өшіру",
        "Конкуренты": "Бәсекелестер",
        "Новый поиск": "Жаңа іздеу",
        "Открыть полный отчёт": "Толық есепті ашу",
        "Создать контент-план": "Контент-жоспар жасау",
        "Создать пост по отчёту": "Есеп бойынша жазба жасау",
        "Пост о результате": "Нәтиже туралы жазба",
        "Повторить ИИ-анализ": "AI талдауын қайталау",
        "Открыть источники": "Дереккөздерді ашу",
        "Создать план по доступным данным": "Бар деректер бойынша жоспар жасау",
        "Да, удалить контекст": "Иә, контексті жою",
        "Отмена": "Бас тарту",
        "Одобрить": "Бекіту",
        "Создать заново": "Қайта жасау",
        "Редактировать": "Өңдеу",
        "Отклонить": "Қабылдамау",
        "Сохранить в Notion": "Notion-ға сақтау",
        "Опубликовать в Telegram": "Telegram-да жариялау",
        "Запланировать": "Жоспарлау",
        "Открыть черновики": "Нобайларды ашу",
        "Главное меню:": "Негізгі мәзір:",
        "Выберите действие:": "Әрекетті таңдаңыз:",
        "Выберите тип поста:": "Жазба түрін таңдаңыз:",
        "Настройки:": "Баптаулар:",
        "Источники:": "Дереккөздер:",
        "Ещё:": "Қосымша:",
        "Отчёты\n\nВыберите, что открыть:": "Есептер\n\nАшатын бөлімді таңдаңыз:",
        "Язык интерфейса:": "Интерфейс тілі:",
        "Язык изменён на Қазақша.": "Тіл Қазақша болып өзгертілді.",
        "Эта кнопка устарела. Откройте /start и выберите действие заново.":
            "Бұл батырма ескірген. /start ашып, әрекетті қайта таңдаңыз.",
        "Growly управляет источниками, рыночной аналитикой, контент-планами, ИИ-черновиками и согласованием через Telegram и Notion.":
            "Growly дереккөздерді, нарық талдауын, контент-жоспарларды, AI нобайларын және Telegram мен Notion арқылы бекітуді басқарады.",
    },
}


def normalize_language(value: str | None) -> str:
    code = (value or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def current_language() -> str:
    return normalize_language(_current_language.get())


def set_current_language(language: str | None) -> str:
    normalized = normalize_language(language)
    _current_language.set(normalized)
    return normalized


def tr(source: str, language: str | None = None, **values: Any) -> str:
    lang = normalize_language(language) if language else current_language()
    translated = TRANSLATIONS.get(lang, {}).get(source, source)
    return translated.format(**values) if values else translated


def language_setting_key(chat_id: int | str) -> str:
    return f"telegram_language:{chat_id}"


async def load_language(chat_id: int | str, fallback: str | None = None) -> str:
    def load() -> str | None:
        with session_scope() as session:
            return SettingsRepository(session).get(language_setting_key(chat_id))

    try:
        saved = await asyncio.to_thread(load)
    except Exception:
        logger.warning("Could not load Telegram language preference.", exc_info=True)
        saved = None
    return normalize_language(saved or fallback)


async def save_language(chat_id: int | str, language: str) -> str:
    normalized = normalize_language(language)

    def save() -> None:
        with session_scope() as session:
            SettingsRepository(session).set(
                language_setting_key(chat_id),
                normalized,
            )

    await asyncio.to_thread(save)
    set_current_language(normalized)
    return normalized
