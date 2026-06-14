from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

from telegram import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    InputFile,
    Update,
)
from telegram.constants import ChatType
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from app.bot.keyboards import (
    approval_keyboard,
    approved_keyboard,
    competitor_report_actions_keyboard,
    create_post_menu_keyboard,
    main_menu_keyboard,
    market_scan_actions_keyboard,
    market_scan_pending_keyboard,
    more_menu_keyboard,
    new_business_confirmation_keyboard,
    report_post_type_keyboard,
    reports_menu_keyboard,
    settings_menu_keyboard,
    source_actions_keyboard,
    sources_menu_keyboard,
)
from app.bot.states import BotState
from app.config import get_settings
from app.database import session_scope
from app.repositories.logs_repo import LogsRepository
from app.repositories.users_repo import UsersRepository
from app.services.content_plan_service import ContentPlanService
from app.services.content_types import content_type_label
from app.services.business_context_service import BusinessContextService
from app.services.draft_service import DraftService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notion_service import NotionService
from app.services.report_service import ReportService
from app.services.review_analysis_service import ReviewAnalysisService
from app.services.source_analysis_service import SourceAnalysisService
from app.services.source_discovery_service import SourceDiscoveryService
from app.services.telegram_service import TelegramService
from app.utils.errors import GrowlyError
from app.utils.text import truncate

logger = logging.getLogger(__name__)
STALE_CALLBACK_MESSAGE = (
    "Эта кнопка устарела. Откройте /start и выберите действие заново."
)

MENU_TEXT = (
    "Growly управляет источниками, рыночной аналитикой, контент-планами, "
    "AI-черновиками и согласованием через Telegram и Notion."
)

HELP_TEXT = """Доступные команды:
/start — регистрация и главное меню
/add_source — добавить источник
/sources — показать источники по типу и статусу
/disable_source — отключить источник
/import_source_items — импортировать материалы конкурентов
/discover_sources — найти публичные источники и конкурентов через Tavily
/monitor_sources — проверить публичную информацию об активных источниках
/web_search — найти и сохранить публичные веб-источники через Tavily
/market_scan — выполнить рыночный поиск и AI-анализ
/retry_analysis — повторить AI-анализ сохранённых результатов поиска
/status — показать состояние последней длительной задачи
/create_post — создать пост
/create_case — создать пост о результате клиента: ситуация, действия, результат
/content_plan — недельный контент-план
/generate_from_plan — создать черновик из контент-плана
/competitor_report — конкурентный отчёт
/review_analysis — анализ отзывов и комментариев
/update_publication_metrics — обновить метрики публикации
/performance_report — создать отчёт по эффективности
/drafts — ожидающие согласования черновики
/reports — последние отчёты
/sync_notion — синхронизация с Notion
/new_business — удалить старый бизнес-контекст и начать заново
/help — справка
/cancel — отменить текущий ввод"""


PRIVATE_BOT_COMMANDS = [
    BotCommand("start", "Регистрация и главное меню"),
    BotCommand("add_source", "Добавить источник"),
    BotCommand("sources", "Источники по типу и статусу"),
    BotCommand("disable_source", "Отключить источник"),
    BotCommand("import_source_items", "Импорт материалов конкурентов"),
    BotCommand("discover_sources", "Найти публичные источники"),
    BotCommand("monitor_sources", "Проверить активные источники"),
    BotCommand("web_search", "Поиск публичных веб-источников"),
    BotCommand("market_scan", "Рыночный поиск и AI-анализ"),
    BotCommand("retry_analysis", "Повторить AI-анализ сохранённого поиска"),
    BotCommand("status", "Статус последней длительной задачи"),
    BotCommand("create_post", "Создать пост"),
    BotCommand("create_case", "Пост о результате клиента"),
    BotCommand("content_plan", "Создать контент-план"),
    BotCommand("generate_from_plan", "Создать черновик из плана"),
    BotCommand("competitor_report", "Создать конкурентный отчёт"),
    BotCommand("review_analysis", "Проанализировать отзывы"),
    BotCommand("update_publication_metrics", "Обновить метрики"),
    BotCommand("performance_report", "Отчёт по эффективности"),
    BotCommand("drafts", "Ожидающие черновики"),
    BotCommand("reports", "Последние отчёты"),
    BotCommand("sync_notion", "Синхронизировать Notion"),
    BotCommand("new_business", "Начать контекст нового бизнеса"),
    BotCommand("help", "Справка"),
    BotCommand("cancel", "Отменить ввод"),
]

GROUP_BOT_COMMANDS: list[BotCommand] = []

POST_TYPE_PRESETS = {
    "Promo post": (
        "promo_post",
        "Опишите предложение, аудиторию, подтверждённые преимущества, условия и CTA.",
    ),
    "Educational post": (
        "educational_post",
        "Опишите тему, аудиторию, практический вопрос или процесс, факты и CTA.",
    ),
    "Client result post": (
        "case_post",
        "Опишите исходную ситуацию, выполненные действия, подтверждённый результат и CTA.",
    ),
    "Case post": (
        "case_post",
        "Опишите исходную ситуацию, выполненные действия, подтверждённый результат и CTA.",
    ),
    "FAQ post": (
        "faq_post",
        "Пришлите реальные вопросы клиентов, подтверждённые ответы, контекст и CTA.",
    ),
    "News post": (
        "news_post",
        "Опишите подтверждённую новость: что изменилось, для кого, дату при наличии и CTA.",
    ),
    "Instagram caption": (
        "instagram_caption",
        "Опишите продукт/предложение, аудиторию, факты и CTA для Instagram-подписи.",
    ),
    "Custom post": (
        None,
        "Опишите тип контента, продукт или услугу, аудиторию, задачу, факты, канал и CTA.",
    ),
    "Create one-off post": (
        None,
        "Опишите тип контента, продукт или услугу, аудиторию, задачу, факты, канал и CTA.",
    ),
}


async def register_commands(application: Any) -> None:
    await application.bot.set_my_commands(
        GROUP_BOT_COMMANDS,
        scope=BotCommandScopeDefault(),
    )
    await application.bot.set_my_commands(
        PRIVATE_BOT_COMMANDS,
        scope=BotCommandScopeAllPrivateChats(),
    )
    await application.bot.set_my_commands(
        GROUP_BOT_COMMANDS,
        scope=BotCommandScopeAllGroupChats(),
    )
    await application.bot.set_my_commands(
        GROUP_BOT_COMMANDS,
        scope=BotCommandScopeAllChatAdministrators(),
    )


async def answer_callback_safely(
    query: Any,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int | None,
    **kwargs: Any,
) -> bool:
    try:
        await query.answer(**kwargs)
        return True
    except BadRequest:
        logger.warning("Telegram callback query expired before it was answered.")
        if chat_id is not None:
            await context.bot.send_message(
                chat_id,
                STALE_CALLBACK_MESSAGE,
                reply_markup=main_menu_keyboard(),
            )
        return False


async def edit_callback_markup_safely(
    query: Any,
    reply_markup: Any,
) -> None:
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except BadRequest:
        logger.warning("Telegram callback message markup is no longer editable.")


async def generate_content_plan_with_progress(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    business_context: dict[str, Any] | str | None,
) -> list[Any]:
    service = ContentPlanService()

    async def progress(message: str) -> None:
        await context.bot.send_message(chat_id, message)
        logger.info("telegram_response_sent")

    items = await service.generate_weekly_plan(
        business_context,
        progress=progress,
    )
    if service.reduced_context_used:
        await context.bot.send_message(
            chat_id,
            (
                "Детальный контекст источников был сокращён из-за ограничения "
                "размера Groq. Контент-план создан по сводке отчетов и ключевым "
                "доказательствам."
            ),
        )
    return items


async def format_notion_sync_result(
    service: NotionService,
    counts: dict[str, int],
) -> str:
    links = await service.configured_database_links()
    lines = [
        "Синхронизация Notion завершена.",
        f"Source Items updated: {counts.get('source_items', 0)}",
        f"Reports updated: {counts.get('reports', 0)}",
        f"Content Calendar updated: {counts.get('content', 0)}",
        f"Drafts updated: {counts.get('drafts', 0)}",
    ]
    if counts.get("content", 0) == 0:
        lines.append(
            "Content Calendar не изменился, потому что новые content plan "
            "items не были созданы."
        )
    if links:
        lines.append("")
        lines.extend(
            f"{label}: {url}"
            for label, url in links.items()
        )
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.effective_message:
        return

    def save_user() -> None:
        with session_scope() as session:
            UsersRepository(session).upsert_telegram_user(
                telegram_chat_id=str(chat.id),
                telegram_username=user.username,
                full_name=user.full_name,
            )

    await asyncio.to_thread(save_user)
    await update.effective_message.reply_text(
        f"{MENU_TEXT}\n\nВыберите действие:", reply_markup=main_menu_keyboard()
    )


async def ensure_telegram_user_id(update: Update) -> int | None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return None

    def save_user() -> int:
        with session_scope() as session:
            saved = UsersRepository(session).upsert_telegram_user(
                telegram_chat_id=str(chat.id),
                telegram_username=user.username,
                full_name=user.full_name,
            )
            return int(saved.id)

    return await asyncio.to_thread(save_user)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            HELP_TEXT, reply_markup=main_menu_keyboard()
        )


async def main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
    return ConversationHandler.END


async def sources_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Источники:",
            reply_markup=sources_menu_keyboard(),
        )


async def more_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Инструменты:",
            reply_markup=more_menu_keyboard(),
        )


async def reports_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Отчёты:",
            reply_markup=reports_menu_keyboard(),
        )


async def settings_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Настройки:",
            reply_markup=settings_menu_keyboard(),
        )


async def create_post_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    context.user_data.pop("post_type", None)
    if update.effective_message:
        await update.effective_message.reply_text(
            "Выберите тип поста:",
            reply_markup=create_post_menu_keyboard(),
        )
    return ConversationHandler.END


async def settings_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message:
        return
    settings = get_settings()
    github_configured = bool(
        settings.github_models_token
        and settings.github_models_token.get_secret_value().strip()
    )
    groq_configured = bool(
        settings.groq_api_key
        and settings.groq_api_key.get_secret_value().strip()
    )
    notion_configured = bool(
        settings.notion_api_key
        and settings.notion_api_key.get_secret_value().strip()
        and (settings.notion_root_page_id or "").strip()
    )
    lines = [
        "Настройки Growly:",
        f"AI primary: {settings.ai_primary_provider}",
        f"GitHub Models: {'configured' if github_configured else 'not configured'}",
        f"AI fallback: {settings.ai_fallback_provider}",
        f"Groq: {'configured' if groq_configured else 'not configured'}",
        f"Search provider: {settings.search_provider or 'not configured'}",
        f"Notion: {'configured' if notion_configured else 'not configured'}",
        (
            "Telegram publishing: configured"
            if settings.telegram_publish_target()
            else "Telegram publishing: not configured"
        ),
        f"Scheduler: {'enabled' if settings.scheduler_enabled else 'disabled'}",
        f"Timezone: {settings.timezone}",
        "",
        "Секретные ключи и токены не показываются.",
    ]
    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=settings_menu_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.effective_chat
    task_entry = (
        context.bot_data.get("market_scan_tasks", {}).get(chat.id)
        if chat
        else None
    )
    context.user_data.clear()
    if task_entry:
        task_entry["task"].cancel()
    if update.effective_message:
        message = (
            "Текущий ввод отменён. Запущена отмена Market Scan."
            if task_entry
            else "Текущий ввод отменён."
        )
        message += (
            " Если фоновая операция не остановится, перезапустите бота."
        )
        await update.effective_message.reply_text(
            message,
            reply_markup=main_menu_keyboard(),
        )
    return ConversationHandler.END


async def task_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message:
        return
    user_id = await ensure_telegram_user_id(update)
    if user_id is None:
        await update.effective_message.reply_text(
            "Не удалось определить пользователя.",
            reply_markup=main_menu_keyboard(),
        )
        return
    job = await MarketIntelligenceService().latest_market_scan_job(user_id)
    if job is None:
        await update.effective_message.reply_text(
            "Длительные задачи ещё не запускались.",
            reply_markup=main_menu_keyboard(),
        )
        return
    lines = [
        f"Задача: {job['task_type']}",
        f"Статус: {job['status']}",
        f"Текущий шаг: {job['current_step'] or 'не указан'}",
        f"Сохранено источников: {job['sources_count']}",
        f"Статус отчёта: {job['report_status'] or 'ещё не создан'}",
    ]
    if job["error_message"]:
        lines.append(f"Последняя ошибка: {job['error_message']}")
    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )


async def new_business_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Начать контекст нового бизнеса?\n\n"
            "Будут безвозвратно удалены из Supabase: источники, результаты поиска, "
            "отчёты, отзывы, контент-планы, черновики, согласования, публикации и "
            "настройки business_*.\n\n"
            "Связанные страницы Notion будут архивированы. Сообщения, уже "
            "опубликованные в Telegram-группе, пользователи, API-ключи и настройки "
            "интеграций останутся.",
            reply_markup=new_business_confirmation_keyboard(),
        )
    return ConversationHandler.END


async def new_business_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return
    await edit_callback_markup_safely(query, None)
    if query.data == "business_reset:cancel":
        await context.bot.send_message(
            chat.id,
            "Сброс отменён.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await context.bot.send_message(
        chat.id,
        "Удаляю старый бизнес-контекст и архивирую связанные страницы Notion…",
    )
    result = await BusinessContextService().reset()
    context.user_data.clear()
    details = ", ".join(
        f"{name}: {count}"
        for name, count in result.deleted_counts.items()
        if count
    )
    lines = [
        "Контекст очищен. Можно начинать работу с новым бизнесом.",
        f"Удалено записей из Supabase: {result.deleted_total}.",
        f"Архивировано страниц Notion: {result.notion_archived}.",
    ]
    if details:
        lines.append(f"По таблицам: {details}.")
    if result.notion_missing:
        lines.append(
            f"Страниц Notion не найдено: {result.notion_missing}."
        )
    if result.notion_failed:
        lines.append(
            f"Не удалось архивировать страниц Notion: {result.notion_failed}. "
            "Supabase-контекст при этом очищен."
        )
    lines.append("Начните с /market_scan или /web_search.")
    await context.bot.send_message(
        chat.id,
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )


async def create_post_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Опишите тип контента, продукт/услугу, аудиторию, главную боль, "
            "бизнес-контекст, канал, допустимые факты и CTA. Например: "
            "«Тип контента: pain-point post». "
            "Не добавляйте конфиденциальные данные без разрешения на публикацию."
        )
    return BotState.WAITING_POST


async def create_post_type_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> BotState:
    if not update.effective_message or not update.effective_message.text:
        return BotState.WAITING_POST
    post_type, prompt = POST_TYPE_PRESETS.get(
        update.effective_message.text,
        (None, "Опишите задачу, аудиторию, факты, канал и CTA."),
    )
    if post_type:
        context.user_data["post_type"] = post_type
    else:
        context.user_data.pop("post_type", None)
    await update.effective_message.reply_text(prompt)
    return BotState.WAITING_POST


async def create_post_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_message.text:
        return BotState.WAITING_POST
    await update.effective_message.reply_text("Генерирую и сохраняю черновик…")
    brief = update.effective_message.text
    post_type = context.user_data.pop("post_type", None)
    if post_type:
        brief = f"Content type: {post_type}\n{brief}"
    draft = await DraftService().create_post({"brief": brief})
    await send_draft(update, context, draft)
    return ConversationHandler.END


async def create_case_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Опишите результат клиента: какая была ситуация, что вы сделали и "
            "какой подтверждённый результат получили. Имена клиентов и компаний "
            "не попадут в пост без вашего явного разрешения."
        )
    return BotState.WAITING_CASE


async def create_case_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_message.text:
        return BotState.WAITING_CASE
    await update.effective_message.reply_text("Генерирую и сохраняю кейс…")
    draft = await DraftService().create_case_post(
        {"case_details": update.effective_message.text, "channel": "Telegram"}
    )
    await send_draft(update, context, draft)
    return ConversationHandler.END


async def review_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Вставьте отзывы или комментарии одним сообщением. "
            "Growly выделит боли, возражения, вопросы, проблемы доверия, идеи и риски."
        )
    return BotState.WAITING_REVIEWS


async def review_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_message.text:
        return BotState.WAITING_REVIEWS
    await update.effective_message.reply_text("Анализирую и сохраняю выводы…")
    review = await ReviewAnalysisService().analyze(update.effective_message.text)
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        review.ai_summary or "Анализ сохранён.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def add_source_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["new_source"] = {}
    if update.effective_message:
        await update.effective_message.reply_text("Название источника:")
    return BotState.ADD_SOURCE_NAME


async def add_source_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> BotState:
    context.user_data["new_source"]["name"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Тип: Instagram / Telegram / TikTok / YouTube / Website / Other"
    )
    return BotState.ADD_SOURCE_TYPE


async def add_source_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> BotState:
    context.user_data["new_source"]["source_type"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("URL или username источника:")
    return BotState.ADD_SOURCE_URL


async def add_source_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> BotState:
    context.user_data["new_source"]["url"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Категория: real estate / construction / barter / B2B / development / "
        "investment / equipment / materials / other"
    )
    return BotState.ADD_SOURCE_CATEGORY


async def add_source_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["new_source"]["category"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Приоритет: high / medium / low")
    return BotState.ADD_SOURCE_PRIORITY


async def add_source_priority(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    value = update.effective_message.text.strip().lower()
    if value not in {"high", "medium", "low"}:
        await update.effective_message.reply_text("Введите high, medium или low.")
        return BotState.ADD_SOURCE_PRIORITY
    context.user_data["new_source"]["priority"] = value
    await update.effective_message.reply_text(
        "Частота проверки: daily / twice_weekly / weekly"
    )
    return BotState.ADD_SOURCE_FREQUENCY


async def add_source_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    value = update.effective_message.text.strip().lower()
    if value not in {"daily", "twice_weekly", "weekly"}:
        await update.effective_message.reply_text(
            "Введите daily, twice_weekly или weekly."
        )
        return BotState.ADD_SOURCE_FREQUENCY
    payload = dict(context.user_data.get("new_source") or {})
    payload["check_frequency"] = value
    source = await SourceAnalysisService().add_source(**payload)
    context.user_data.pop("new_source", None)
    await update.effective_message.reply_text(
        f"Источник #{source.id} сохранён: {source.name}.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await SourceAnalysisService().list_sources(active_only=False)
    if not rows:
        await update.effective_message.reply_text(
            "Сохранённых источников нет. Используйте /discover_sources или /add_source.",
            reply_markup=main_menu_keyboard(),
        )
        return
    groups: dict[tuple[str, str], list[Any]] = {}
    for row in rows:
        groups.setdefault(
            (row.source_type or "Other", row.status or "unknown"), []
        ).append(row)
    lines = ["Сохранённые источники по типу и статусу:"]
    for (source_type, status), items in sorted(groups.items()):
        lines.append(f"\n{source_type} · {status}")
        lines.extend(
            f"#{item.id} {item.name} · {item.url or 'URL не указан'}"
            for item in items
        )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=source_actions_keyboard(rows),
    )


async def discover_sources_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["source_discovery"] = {}
    await update.effective_message.reply_text("Укажите нишу или рынок:")
    return BotState.DISCOVER_SOURCES_NICHE


async def discover_sources_niche(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["source_discovery"]["niche"] = (
        update.effective_message.text.strip()
    )
    await update.effective_message.reply_text(
        "Укажите регион, например: Казахстан / Алматы / global:"
    )
    return BotState.DISCOVER_SOURCES_REGION


async def discover_sources_region(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["source_discovery"]["region"] = (
        update.effective_message.text.strip()
    )
    await update.effective_message.reply_text(
        "Какие платформы искать? Через запятую: "
        "website, Telegram, Instagram, TikTok, YouTube"
    )
    return BotState.DISCOVER_SOURCES_PLATFORMS


async def discover_sources_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    payload = dict(context.user_data.get("source_discovery") or {})
    payload["platforms"] = [
        value.strip() for value in update.effective_message.text.split(",")
    ]
    await update.effective_message.reply_text(
        "Ищу публичные источники через Tavily и сохраняю кандидатов на проверку…"
    )
    rows = await SourceDiscoveryService().discover_sources(**payload)
    context.user_data.pop("source_discovery", None)
    if not rows:
        await update.effective_message.reply_text(
            "Надёжных кандидатов в публичных результатах не найдено. "
            "Попробуйте уточнить нишу, регион или платформы.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    lines = [
        f"Найдено кандидатов: {len(rows)}.",
        "Новые источники имеют статус requires_review.",
        "",
    ]
    lines.extend(
        f"#{row.id} · {row.source_type} · {row.status}\n"
        f"{row.name}\n{row.url or 'URL не указан'}"
        for row in rows
    )
    lines.extend(
        [
            "",
            "Важно: Tavily показывает публичные поисковые свидетельства. "
            "Это не полный мониторинг Instagram, TikTok или YouTube.",
            "Telegram-каналы здесь только обнаруживаются; полный сбор постов "
            "требует отдельного Telegram collector.",
            "Метрики YouTube Shorts требуют YouTube Data API.",
        ]
    )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=source_actions_keyboard(rows),
    )
    return ConversationHandler.END


async def source_action_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return
    _, action, source_id_text = query.data.split(":", 2)
    service = SourceDiscoveryService()
    if action == "approve":
        source = await service.approve_source(int(source_id_text))
        text = f"Источник #{source.id} подтверждён и теперь активен."
    else:
        source = await service.disable_source(int(source_id_text))
        text = f"Источник #{source.id} отключён."
    await context.bot.send_message(
        chat.id,
        text,
        reply_markup=main_menu_keyboard(),
    )


async def monitor_sources(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text(
        "Проверяю публичную веб-информацию об активных источниках. "
        "Это поиск свидетельств через Tavily, а не полный scraping платформ…"
    )
    report, items = await SourceDiscoveryService().monitor_active_sources()
    summary = report.body or report.report_text or "Сводка сохранена."
    header = (
        f"Проверено активных источников: {report.sources_count}.\n"
        f"Сохранено findings: {len(items)}.\n\n"
    )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        header + summary,
        reply_markup=main_menu_keyboard(),
    )


async def disable_source_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    await sources(update, context)
    await update.effective_message.reply_text(
        "Введите ID или точное название источника для отключения:"
    )
    return BotState.DISABLE_SOURCE


async def disable_source_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    source = await SourceAnalysisService().disable_source(
        update.effective_message.text
    )
    await update.effective_message.reply_text(
        f"Источник #{source.id} отключён.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def import_source_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    await sources(update, context)
    await update.effective_message.reply_text(
        "Введите ID или точное название источника для импорта:"
    )
    return BotState.IMPORT_SOURCE_SELECT


async def import_source_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    source = await SourceAnalysisService().find_source(update.effective_message.text)
    if source is None or source.status != "active":
        await update.effective_message.reply_text(
            "Активный источник не найден. Повторите ID или название."
        )
        return BotState.IMPORT_SOURCE_SELECT
    context.user_data["import_source_id"] = source.id
    await update.effective_message.reply_text(
        "Вставьте посты, ссылки, captions, наблюдения, метрики, комментарии или "
        "экспортированный текст. Разделяйте элементы пустой строкой или строкой ---."
    )
    return BotState.IMPORT_SOURCE_TEXT


async def import_source_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.effective_message.reply_text("Анализирую и сохраняю материалы…")
    items = await SourceAnalysisService().import_source_items(
        source_id=int(context.user_data["import_source_id"]),
        raw_text=update.effective_message.text,
    )
    context.user_data.pop("import_source_id", None)
    await update.effective_message.reply_text(
        f"Импортировано и проанализировано материалов: {len(items)}.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def web_search_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState | int:
    chat = update.effective_chat
    if update.callback_query:
        if not await answer_callback_safely(
            update.callback_query,
            context,
            chat.id if chat else None,
            show_alert=not chat or chat.type != ChatType.PRIVATE,
        ):
            return ConversationHandler.END
    if not chat or chat.type != ChatType.PRIVATE:
        return ConversationHandler.END
    if update.effective_message:
        await update.effective_message.reply_text("Что ищем?")
    return BotState.WEB_SEARCH_QUERY


async def web_search_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_message.text:
        return BotState.WEB_SEARCH_QUERY
    query = update.effective_message.text.strip()
    await update.effective_message.reply_text("Ищу публичные источники через Tavily…")
    items = await MarketIntelligenceService().web_search(query)
    lines = [
        f"Найдено и сохранено результатов: {len(items)}.",
        "",
        "Топ-5:",
    ]
    lines.extend(
        f"{index}. {item.title}\n{item.url}"
        for index, item in enumerate(items[:5], start=1)
    )
    lines.extend(
        [
            "",
            "Supabase IDs: "
            + (", ".join(str(item.id) for item in items) or "нет"),
            "Дальше: /market_scan или /competitor_report",
        ]
    )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def market_scan_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState | int:
    chat = update.effective_chat
    task_entry = (
        context.bot_data.get("market_scan_tasks", {}).get(chat.id)
        if chat
        else None
    )
    if task_entry and not task_entry["task"].done():
        if update.effective_message:
            await update.effective_message.reply_text(
                "Market Scan уже выполняется. Используйте /status или /cancel.",
                reply_markup=main_menu_keyboard(),
            )
        return ConversationHandler.END
    context.user_data["market_scan"] = {}
    if update.effective_message:
        await update.effective_message.reply_text("Укажите рынок, нишу или тему:")
    return BotState.MARKET_SCAN_NICHE


async def market_scan_niche(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["market_scan"]["niche"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Укажите регион и язык анализа, например: Казахстан, русский:"
    )
    return BotState.MARKET_SCAN_REGION


async def market_scan_region(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["market_scan"]["region_language"] = (
        update.effective_message.text.strip()
    )
    await update.effective_message.reply_text(
        "Укажите названия или ключевые слова конкурентов. Если их нет, отправьте «нет»:"
    )
    return BotState.MARKET_SCAN_COMPETITORS


async def market_scan_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_chat:
        return ConversationHandler.END
    payload = dict(context.user_data.get("market_scan") or {})
    payload["competitor_keywords"] = update.effective_message.text.strip()
    context.user_data.pop("market_scan", None)
    user_id = await ensure_telegram_user_id(update)
    service = MarketIntelligenceService()
    job = await service.create_market_scan_job(user_id, payload["niche"])
    chat_id = update.effective_chat.id

    async def progress(message: str) -> None:
        await context.bot.send_message(chat_id, message)
        logger.info("telegram_response_sent")

    async def run_background_scan() -> None:
        try:
            report, items = await service.run_market_scan(
                **payload,
                user_id=user_id,
                job_id=job.id,
                progress=progress,
            )
            await send_market_scan_result(
                context.bot,
                chat_id,
                report,
                items,
            )
            logger.info("telegram_response_sent")
        except asyncio.CancelledError:
            await service.cancel_market_scan_job(job.id)
            raise
        except Exception as exc:
            safe_error = (
                str(exc)
                if isinstance(exc, GrowlyError)
                else f"Unexpected {type(exc).__name__}"
            )
            await service.fail_market_scan_job(job.id, safe_error)
            logger.exception(
                "Market scan background task failed: %s",
                type(exc).__name__,
            )
            await context.bot.send_message(
                chat_id,
                "Market Scan завершился с ошибкой. Сохранённые источники не удалены. "
                "Проверьте /status и повторите попытку.",
                reply_markup=main_menu_keyboard(),
            )
            logger.info("telegram_response_sent")

    tasks = context.bot_data.setdefault("market_scan_tasks", {})
    task = context.application.create_task(run_background_scan())
    tasks[chat_id] = {"task": task, "job_id": job.id}

    def cleanup(completed_task: asyncio.Task[Any]) -> None:
        current = tasks.get(chat_id)
        if current and current["task"] is completed_task:
            tasks.pop(chat_id, None)

    task.add_done_callback(cleanup)
    return ConversationHandler.END


async def send_market_scan_result(
    bot: Any,
    chat_id: int,
    report: Any,
    items: list[Any],
) -> None:
    analysis = report.raw_json or {}
    if report.status == "search_saved_analysis_pending":
        message = (
            "Источники сохранены, но AI-анализ пока не завершился. "
            "Можно повторить позже."
        )
        await TelegramService().send_long_text(
            bot,
            chat_id,
            (
                f"{message}\n\n"
                f"Сохранено источников: {len(items)}\n"
                f"Статус отчёта: {report.status}"
            ),
            reply_markup=market_scan_pending_keyboard(report.id),
        )
        return

    def top(value: Any, limit: int = 5) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        rows = value if isinstance(value, list) else []
        return "\n".join(f"- {row}" for row in rows[:limit]) or "- Нет данных"

    summary = "\n\n".join(
        [
            f"Market scan #{report.id}",
            str(analysis.get("executive_summary") or report.summary or "Нет вывода."),
            f"Проанализировано источников: {len(items)}",
            "Доминирующие темы:\n" + top(analysis.get("dominant_topics")),
            "Боли аудитории:\n" + top(analysis.get("audience_pains")),
            "Контентные пробелы:\n" + top(analysis.get("content_gaps")),
            "Топ-5 идей:\n" + top(analysis.get("content_ideas")),
            "Ограничения:\n"
            + top(analysis.get("risks_and_limitations"), limit=8),
        ]
    )
    await TelegramService().send_long_text(
        bot,
        chat_id,
        summary,
        reply_markup=market_scan_actions_keyboard(report.id),
    )


async def send_competitor_report_summary(
    bot: Any,
    chat_id: int,
    report: Any,
) -> None:
    payload = report.raw_json or {}

    def names() -> str:
        rows = payload.get("competitors")
        if not isinstance(rows, list):
            return "Не идентифицированы по сохранённым данным"
        values = [
            str(row.get("competitor") or "").strip()
            for row in rows[:5]
            if isinstance(row, dict) and str(row.get("competitor") or "").strip()
        ]
        return ", ".join(values) or "Не идентифицированы по сохранённым данным"

    def top(key: str, limit: int = 3) -> str:
        rows = payload.get(key)
        values = rows if isinstance(rows, list) else []
        return "\n".join(f"- {truncate(str(value), 180)}" for value in values[:limit]) or (
            "- Нет подтверждённых данных"
        )

    message = "\n\n".join(
        [
            f"Конкурентный отчёт #{report.id} сохранён.",
            truncate(
                str(
                    payload.get("executive_summary")
                    or report.summary
                    or "Нет подтверждённого вывода."
                ),
                700,
            ),
            f"Конкуренты: {names()}",
            "Контентные пробелы:\n" + top("content_gaps"),
            "Действия на неделю:\n" + top("actions_this_week", limit=5),
            f"Проверено источников: {report.sources_count}",
        ]
    )
    await bot.send_message(
        chat_id,
        message,
        reply_markup=competitor_report_actions_keyboard(report.id),
    )


async def retry_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    user_id = await ensure_telegram_user_id(update)
    service = MarketIntelligenceService()
    latest = (
        await service.latest_market_scan_job(user_id)
        if user_id is not None
        else None
    )
    await schedule_retry_analysis(
        context,
        update.effective_chat.id,
        report_id=None,
        job_id=int(latest["id"]) if latest else None,
    )


async def schedule_retry_analysis(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    *,
    report_id: int | None,
    job_id: int | None,
) -> None:
    tasks = context.bot_data.setdefault("market_scan_tasks", {})
    current = tasks.get(chat_id)
    if current and not current["task"].done():
        await context.bot.send_message(
            chat_id,
            "Market Scan уже выполняется. Используйте /status или /cancel.",
            reply_markup=main_menu_keyboard(),
        )
        return

    service = MarketIntelligenceService()
    await context.bot.send_message(
        chat_id,
        "Повторяю AI-анализ по сохранённым источникам…",
    )
    logger.info("telegram_response_sent")

    async def progress(message: str) -> None:
        await context.bot.send_message(chat_id, message)
        logger.info("telegram_response_sent")

    async def run_retry() -> None:
        try:
            report, items = await service.retry_latest_analysis(
                report_id,
                progress=progress,
            )
            await send_market_scan_result(
                context.bot,
                chat_id,
                report,
                items,
            )
            logger.info("telegram_response_sent")
        except asyncio.CancelledError:
            await service.cancel_market_scan_job(job_id)
            raise
        except ValueError as exc:
            await context.bot.send_message(
                chat_id,
                str(exc),
                reply_markup=main_menu_keyboard(),
            )
            logger.info("telegram_response_sent")
        except Exception as exc:
            safe_error = (
                str(exc)
                if isinstance(exc, GrowlyError)
                else f"Unexpected {type(exc).__name__}"
            )
            await service.fail_market_scan_job(job_id, safe_error)
            await context.bot.send_message(
                chat_id,
                "Повторный AI-анализ завершился с ошибкой. Проверьте /status.",
                reply_markup=main_menu_keyboard(),
            )
            logger.info("telegram_response_sent")

    task = context.application.create_task(run_retry())
    tasks[chat_id] = {"task": task, "job_id": job_id}

    def cleanup(completed_task: asyncio.Task[Any]) -> None:
        active = tasks.get(chat_id)
        if active and active["task"] is completed_task:
            tasks.pop(chat_id, None)

    task.add_done_callback(cleanup)


async def market_scan_action_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return
    _, action, report_id_value = query.data.split(":", 2)
    report_id = int(report_id_value)
    if action == "competitor":
        await context.bot.send_message(chat.id, "Формирую конкурентный отчёт…")
        report = await MarketIntelligenceService().generate_competitor_report()
        await send_competitor_report_summary(context.bot, chat.id, report)
    elif action == "content_plan":
        items = await generate_content_plan_with_progress(
            context,
            chat.id,
            {"goal": "Использовать последний market scan и конкурентный отчёт."}
        )
        await context.bot.send_message(
            chat.id,
            f"Контент-план сохранён: {len(items)} элементов.",
            reply_markup=main_menu_keyboard(),
        )
    elif action == "limited_plan":
        items = await generate_content_plan_with_progress(
            context,
            chat.id,
            {
                "goal": (
                    "Создать осторожный контент-план по сохранённым публичным "
                    "source_items. Полный market scan недоступен; не делать "
                    "неподтверждённых выводов."
                ),
                "evidence_limited": True,
            }
        )
        await context.bot.send_message(
            chat.id,
            f"Контент-план по ограниченным данным сохранён: {len(items)} элементов.",
            reply_markup=main_menu_keyboard(),
        )
    elif action == "notion":
        service = NotionService()
        counts = await service.sync_recent_data()
        await context.bot.send_message(
            chat.id,
            await format_notion_sync_result(service, counts),
            reply_markup=main_menu_keyboard(),
        )
    elif action == "retry":
        job_id = await MarketIntelligenceService().market_scan_job_id_for_report(
            report_id
        )
        await schedule_retry_analysis(
            context,
            chat.id,
            report_id=report_id,
            job_id=job_id,
        )
    elif action == "view_sources":
        items = await MarketIntelligenceService().source_items_for_report(
            report_id
        )
        if not items:
            await context.bot.send_message(
                chat.id,
                "No saved source items were found for this report.",
                reply_markup=main_menu_keyboard(),
            )
            return
        lines = [f"Saved source items for market scan #{report_id}:"]
        lines.extend(
            f"{index}. #{item.id} {item.title or 'Untitled'}\n{item.url or 'No URL'}"
            for index, item in enumerate(items, start=1)
        )
        await TelegramService().send_long_text(
            context.bot,
            chat.id,
            "\n\n".join(lines),
            reply_markup=market_scan_pending_keyboard(report_id),
        )


async def report_action_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return

    _, action, report_id_value = query.data.split(":", 2)
    report_id = int(report_id_value)
    service = ReportService()
    report = await service.get_report(report_id)
    if report is None:
        await context.bot.send_message(chat.id, "Отчёт не найден.")
        return

    if action == "view":
        body = report.body or report.report_text or report.summary or "Отчёт пуст."
        await context.bot.send_document(
            chat.id,
            document=InputFile(
                BytesIO(body.encode("utf-8")),
                filename=f"growly-report-{report.id}.txt",
            ),
            caption=f"Полный отчёт #{report.id}.",
        )
    elif action == "content_plan":
        payload = report.raw_json or {}
        items = await generate_content_plan_with_progress(
            context,
            chat.id,
            {
                "goal": f"Создать контент-план по конкурентному отчёту #{report.id}.",
                "latest_competitor_report": {
                    "summary": report.summary,
                    "content_gaps": payload.get("content_gaps", []),
                    "recommended_positioning": payload.get(
                        "recommended_positioning", []
                    ),
                    "actions_this_week": payload.get("actions_this_week", []),
                },
            },
        )
        await context.bot.send_message(
            chat.id,
            f"Контент-план сохранён: {len(items)} элементов.",
            reply_markup=main_menu_keyboard(),
        )
    elif action == "create_post":
        await context.bot.send_message(
            chat.id,
            "Выберите тип поста по выводам отчёта:",
            reply_markup=report_post_type_keyboard(report.id),
        )
    elif action == "notion":
        try:
            url = await service.sync_report_to_notion(report.id)
            message = f"Отчёт #{report.id} синхронизирован с Notion:\n{url}"
        except (TimeoutError, GrowlyError):
            message = (
                f"Отчёт #{report.id} сохранён в Supabase, но синхронизация "
                "с Notion сейчас не завершилась."
            )
        await context.bot.send_message(chat.id, message)


async def report_post_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return

    _, report_id_value, post_type = query.data.split(":", 2)
    report = await ReportService().get_report(int(report_id_value))
    if report is None:
        await context.bot.send_message(chat.id, "Отчёт не найден.")
        return
    payload = report.raw_json or {}
    evidence = {
        "executive_summary": payload.get("executive_summary") or report.summary,
        "content_gaps": payload.get("content_gaps", []),
        "recommended_positioning": payload.get("recommended_positioning", []),
        "actions_this_week": payload.get("actions_this_week", []),
        "source_urls": (payload.get("source_urls") or report.evidence_json or [])[:8],
    }
    await context.bot.send_message(chat.id, "Генерирую черновик по отчёту…")
    draft = await DraftService().create_post(
        {
            "title": f"Post from competitor report #{report.id}",
            "brief": (
                f"Content type: {post_type}\n"
                "Создай пост только по подтверждённым выводам конкурентного отчёта. "
                "Не придумывай цены, результаты или заявления конкурентов.\n"
                + json.dumps(evidence, ensure_ascii=False)
            ),
            "channel": "Telegram",
        }
    )
    await send_draft(update, context, draft)


async def content_plan_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["plan_brief"] = {}
    intelligence = await ContentPlanService().intelligence_status()
    if not any(intelligence.values()):
        await update.effective_message.reply_text(
            "Предупреждение: market scan, competitor report и Source Items не найдены. "
            "План будет основан только на ограниченных внутренних данных."
        )
    await update.effective_message.reply_text(
        "Главная цель недели: leads / trust / education / sales / engagement / "
        "product awareness"
    )
    return BotState.PLAN_GOAL


async def content_plan_goal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["plan_brief"]["goal"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Главная аудитория: small business owners / marketers / B2B / real estate / custom"
    )
    return BotState.PLAN_AUDIENCE


async def content_plan_audience(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["plan_brief"]["audience"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Главный оффер или продукт недели:")
    return BotState.PLAN_OFFER


async def content_plan_offer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["plan_brief"]["offer"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Каналы через запятую: Telegram / Instagram / Reels / WhatsApp / Website"
    )
    return BotState.PLAN_CHANNELS


async def content_plan_channels(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    context.user_data["plan_brief"]["channels"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Интенсивность: light / normal / aggressive"
    )
    return BotState.PLAN_INTENSITY


async def content_plan_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["plan_brief"]["intensity"] = update.effective_message.text.strip()
    items = await generate_content_plan_with_progress(
        context,
        update.effective_chat.id,
        dict(context.user_data["plan_brief"]),
    )
    context.user_data.pop("plan_brief", None)
    lines = [f"Контент-план сохранён: {len(items)} идей."]
    lines.extend(
        f"{index}. #{item.id} · {item.publish_date:%Y-%m-%d %H:%M} · "
        f"{item.content_type} · {item.topic}\nПочему: {item.why_recommended}"
        for index, item in enumerate(items, start=1)
    )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def generate_from_plan_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState | int:
    items = await ContentPlanService().list_draft_items()
    if not items:
        await update.effective_message.reply_text(
            "Нет элементов плана со статусом draft. Сначала используйте /content_plan.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END
    context.user_data["plan_item_choices"] = [item.id for item in items]
    text = ["Выберите номер или ID элемента:"]
    text.extend(
        f"{index}. #{item.id} · {item.channel} · {item.content_type} · {item.topic}"
        for index, item in enumerate(items, start=1)
    )
    await TelegramService().send_long_text(
        context.bot, update.effective_chat.id, "\n".join(text)
    )
    return BotState.PLAN_ITEM_SELECT


async def generate_from_plan_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    value = update.effective_message.text.strip()
    choices = context.user_data.get("plan_item_choices") or []
    if not value.isdigit():
        await update.effective_message.reply_text("Введите номер или числовой ID.")
        return BotState.PLAN_ITEM_SELECT
    number = int(value)
    item_id = choices[number - 1] if 1 <= number <= len(choices) else number
    await update.effective_message.reply_text("Генерирую черновик из плана…")
    draft = await DraftService().create_from_plan(item_id)
    context.user_data.pop("plan_item_choices", None)
    await send_draft(update, context, draft)
    return ConversationHandler.END


async def update_metrics_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState | int:
    publications = await ReportService().list_recent_publications()
    if not publications:
        await update.effective_message.reply_text(
            "Опубликованных материалов для обновления метрик нет.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END
    context.user_data["publication_choices"] = [row.id for row in publications]
    lines = ["Выберите номер или ID публикации:"]
    for index, row in enumerate(publications, start=1):
        published_date = (
            row.published_at.strftime("%Y-%m-%d")
            if row.published_at
            else "дата не указана"
        )
        lines.append(
            f"{index}. #{row.id} · {published_date} · "
            f"{row.draft.title if row.draft else 'Без названия'}"
        )
    await TelegramService().send_long_text(
        context.bot, update.effective_chat.id, "\n".join(lines)
    )
    return BotState.METRICS_PUBLICATION_SELECT


async def update_metrics_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState:
    value = update.effective_message.text.strip()
    choices = context.user_data.get("publication_choices") or []
    if not value.isdigit():
        await update.effective_message.reply_text("Введите номер или числовой ID.")
        return BotState.METRICS_PUBLICATION_SELECT
    number = int(value)
    context.user_data["publication_id"] = (
        choices[number - 1] if 1 <= number <= len(choices) else number
    )
    await update.effective_message.reply_text(
        "Введите: views, reactions, comments, clicks, leads, notes\n"
        "Пример: 1200, 45, 8, 12, 3, Получили вопросы по цене"
    )
    return BotState.METRICS_VALUES


async def update_metrics_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    parts = [part.strip() for part in update.effective_message.text.split(",", 5)]
    if len(parts) < 5 or not all(re.fullmatch(r"\d+", part) for part in parts[:5]):
        await update.effective_message.reply_text(
            "Нужны пять неотрицательных чисел и необязательная заметка через запятую."
        )
        return BotState.METRICS_VALUES
    values = [int(part) for part in parts[:5]]
    notes = parts[5] if len(parts) > 5 else None
    publication = await ReportService().update_publication_metrics(
        int(context.user_data["publication_id"]),
        views=values[0],
        reactions=values[1],
        comments=values[2],
        clicks=values[3],
        leads=values[4],
        notes=notes,
    )
    context.user_data.pop("publication_choices", None)
    context.user_data.pop("publication_id", None)
    await update.effective_message.reply_text(
        f"Метрики публикации #{publication.id} обновлены.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def performance_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text("Формирую отчёт по эффективности…")
    report = await ReportService().generate_weekly_performance_report()
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        report.report_text or "Отчёт сохранён.",
        reply_markup=main_menu_keyboard(),
    )


async def competitor_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> BotState | int:
    if not update.effective_message:
        return ConversationHandler.END
    service = MarketIntelligenceService()
    if not await service.has_source_items():
        await update.effective_message.reply_text(
            "Source Items пока пусты. Введите нишу или тему, чтобы сначала выполнить "
            "поиск, либо используйте /market_scan для выбора региона и конкурентов."
        )
        return BotState.COMPETITOR_REPORT_TOPIC
    await update.effective_message.reply_text("Формирую конкурентный отчёт…")
    report = await service.generate_competitor_report()
    await send_competitor_report_summary(
        context.bot,
        update.effective_chat.id,
        report,
    )
    return ConversationHandler.END


async def competitor_report_topic(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.effective_message or not update.effective_message.text:
        return BotState.COMPETITOR_REPORT_TOPIC
    topic = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Сначала собираю публичные источники, затем формирую конкурентный отчёт…"
    )
    service = MarketIntelligenceService()
    await service.run_market_scan(
        niche=topic,
        region_language="регион и язык не указаны",
        competitor_keywords="нет",
    )
    report = await service.generate_competitor_report(query=topic)
    await send_competitor_report_summary(
        context.bot,
        update.effective_chat.id,
        report,
    )
    return ConversationHandler.END


async def drafts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    pending = await DraftService().list_pending()
    if not pending:
        await update.effective_message.reply_text(
            "Нет черновиков, ожидающих согласования.",
            reply_markup=main_menu_keyboard(),
        )
        return
    for draft in pending:
        await send_draft(update, context, draft)


async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    rows = await ReportService().list_latest()
    if not rows:
        await update.effective_message.reply_text(
            "Отчёты ещё не созданы.", reply_markup=reports_menu_keyboard()
        )
        return
    summary = "\n\n".join(
        (
            f"#{row.id} · {row.title}\n"
            f"{truncate(row.summary or row.body or row.report_text, 220)}"
        )
        for row in rows[:5]
    )
    await update.effective_message.reply_text(
        summary,
        reply_markup=reports_menu_keyboard(),
    )


async def sync_notion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text("Синхронизирую последние данные с Notion…")
    service = NotionService()
    counts = await service.sync_recent_data()
    await update.effective_message.reply_text(
        await format_notion_sync_result(service, counts),
        reply_markup=main_menu_keyboard(),
    )


async def debug_notion_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    status = await NotionService().debug_status()
    lines = [
        f"NOTION_ROOT_PAGE_ID: {status['notion_root_page_id'] or 'not configured'}",
        "",
        "Configured database IDs:",
    ]
    database_ids = status["database_ids"]
    if database_ids:
        lines.extend(
            f"{key}: {value}"
            for key, value in sorted(database_ids.items())
        )
    else:
        lines.append("none")
    lines.extend(["", "Latest Supabase counts:"])
    lines.extend(
        f"{key}: {value}"
        for key, value in status["supabase_counts"].items()
    )
    lines.extend(["", "Latest Notion sync counts:"])
    latest_sync = status["latest_sync_counts"]
    if latest_sync:
        lines.extend(
            f"{key}: {value}"
            for key, value in latest_sync.items()
        )
    else:
        lines.append("none")
    lines.extend(
        [
            "",
            f"Latest report id: {status['latest_report_id'] or 'none'}",
            (
                "Latest content plan count: "
                f"{status['latest_content_plan_count']}"
            ),
        ]
    )
    await TelegramService().send_long_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )


async def send_draft(
    update: Update, context: ContextTypes.DEFAULT_TYPE, draft: Any
) -> None:
    chat = update.effective_chat
    if not chat:
        return
    settings = get_settings()
    rendered = format_draft_message(draft)
    message_id = await TelegramService(settings).send_long_text(
        context.bot,
        chat.id,
        rendered,
        reply_markup=approval_keyboard(draft.id),
    )
    if message_id is not None:
        await DraftService(settings=settings).set_telegram_message(
            draft.id, message_id
        )


def format_draft_message(draft: Any) -> str:
    header = (
        f"Черновик #{draft.id} · версия {draft.version} · статус {draft.status}\n"
        f"Тип контента: {content_type_label(draft.draft_type)}\n"
        f"{draft.title or ''}\n\n"
    )
    metadata = draft.generation_metadata_json or {}
    why = str(metadata.get("why_this_should_work") or "Не указано.").strip()
    risk = str(metadata.get("risk_check") or "Не указано.").strip()
    return (
        f"{header}{draft.draft_text}\n\n"
        f"Почему этот пост\n{why}\n\n"
        f"Проверка рисков\n{risk}"
    )


async def publish_approved_draft(
    bot: Any,
    service: DraftService,
    draft_id: int,
) -> tuple[bool, str]:
    reservation = await service.reserve_publication(draft_id)
    if not reservation.should_publish:
        if reservation.publication.status == "published":
            return False, "already published"
        return False, "publication is already in progress"

    draft = await service.get(draft_id)
    if draft is None:
        await service.fail_publication(reservation.publication.id)
        raise ValueError("Draft was not found.")

    try:
        results = await TelegramService(service.settings).publish_to_targets(
            bot, draft
        )
    except Exception:
        await service.fail_publication(reservation.publication.id)
        raise

    message_ids = [mid for ids in results.values() for mid in ids]
    await service.complete_publication(reservation.publication.id, message_ids)
    return True, f"published to {len(results)} destination(s)"


async def approval_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    if not query or not query.data or not chat:
        return
    if not await answer_callback_safely(
        query,
        context,
        chat.id,
        show_alert=chat.type != ChatType.PRIVATE,
    ):
        return
    if chat.type != ChatType.PRIVATE:
        return
    action, draft_id_text = query.data.split(":", 1)
    draft_id = int(draft_id_text)
    service = DraftService()
    actor = user.full_name if user else str(chat.id)

    if action == "approve":
        await service.record_action(
            draft_id=draft_id,
            telegram_chat_id=str(chat.id),
            action="approve",
            approved_by=actor,
        )
        await edit_callback_markup_safely(
            query,
            approved_keyboard(
                draft_id,
                telegram_publish_enabled=bool(
                    service.settings.telegram_publish_target()
                ),
            ),
        )
        await context.bot.send_message(
            chat.id,
            f"Черновик #{draft_id} одобрен.",
        )
    elif action == "reject":
        await service.record_action(
            draft_id=draft_id,
            telegram_chat_id=str(chat.id),
            action="reject",
        )
        await edit_callback_markup_safely(query, None)
        await context.bot.send_message(chat.id, f"Черновик #{draft_id} отклонён.")
    elif action == "regenerate":
        await service.record_event(
            draft_id=draft_id,
            telegram_chat_id=str(chat.id),
            action="regenerate",
        )
        regenerated = await service.regenerate(draft_id)
        await edit_callback_markup_safely(query, None)
        await send_draft(update, context, regenerated)
    elif action == "notion":
        url = await service.ensure_notion(draft_id)
        await service.record_event(
            draft_id=draft_id,
            telegram_chat_id=str(chat.id),
            action="save_to_notion",
        )
        await context.bot.send_message(chat.id, f"Страница Notion: {url}")
    elif action == "publish":
        published, result = await publish_approved_draft(
            context.bot,
            service,
            draft_id,
        )
        if published:
            await service.record_event(
                draft_id=draft_id,
                telegram_chat_id=str(chat.id),
                action="publish_telegram_group",
            )
            await edit_callback_markup_safely(query, None)
            message = f"Черновик #{draft_id} опубликован в Telegram-группе."
        else:
            message = f"Черновик #{draft_id}: {result}."
        await context.bot.send_message(chat.id, message)


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    error = context.error
    exc_info = (
        (type(error), error, error.__traceback__)
        if isinstance(error, BaseException)
        else None
    )
    logger.error("Telegram update failed: %s", type(error).__name__, exc_info=exc_info)

    def save_log() -> None:
        try:
            with session_scope() as session:
                LogsRepository(session).create(
                    level="ERROR",
                    module="telegram",
                    message="Telegram update failed.",
                    details={"exception_type": type(error).__name__},
                )
        except Exception:
            logger.exception("Could not persist Telegram error.")

    await asyncio.to_thread(save_log)
    effective_message = getattr(update, "effective_message", None)
    if effective_message:
        message = (
            str(error)
            if isinstance(error, GrowlyError)
            else "Не удалось выполнить запрос. Попробуйте позже или проверьте интеграции."
        )
        await effective_message.reply_text(message, reply_markup=main_menu_keyboard())


async def edit_draft_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return ConversationHandler.END
    await answer_callback_safely(query, context, chat.id)
    _, draft_id_text = query.data.split(":", 1)
    context.user_data["edit_draft_id"] = int(draft_id_text)
    await context.bot.send_message(
        chat.id,
        "Пришлите новый текст черновика. Он заменит текущий и снова уйдёт на одобрение.",
    )
    return BotState.EDIT_DRAFT_TEXT


async def edit_draft_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    draft_id = int(context.user_data.pop("edit_draft_id"))
    text = (update.effective_message.text or "").strip()
    if not text:
        await update.effective_message.reply_text("Текст не может быть пустым.")
        context.user_data["edit_draft_id"] = draft_id
        return BotState.EDIT_DRAFT_TEXT
    draft = await DraftService().apply_manual_edit(draft_id, text)
    await update.effective_message.reply_text(
        f"Черновик #{draft.id} обновлён (версия {draft.version})."
    )
    await send_draft(update, context, draft)
    return ConversationHandler.END


def parse_schedule_datetime(text: str) -> datetime:
    raw = text.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d.%m.%Y %H:%M"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.replace(tzinfo=ZoneInfo(get_settings().timezone))
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Unrecognized date/time format.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(get_settings().timezone))
    return parsed


async def schedule_draft_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    chat = update.effective_chat
    if not query or not query.data or not chat:
        return ConversationHandler.END
    await answer_callback_safely(query, context, chat.id)
    _, draft_id_text = query.data.split(":", 1)
    context.user_data["schedule_draft_id"] = int(draft_id_text)
    await context.bot.send_message(
        chat.id,
        "Когда опубликовать? Формат: ГГГГ-ММ-ДД ЧЧ:ММ (например, 2026-07-01 14:30).",
    )
    return BotState.SCHEDULE_DATETIME


async def schedule_draft_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    draft_id = int(context.user_data.get("schedule_draft_id"))
    try:
        when = parse_schedule_datetime(update.effective_message.text or "")
    except ValueError:
        await update.effective_message.reply_text(
            "Не понял дату. Используйте формат 2026-07-01 14:30."
        )
        return BotState.SCHEDULE_DATETIME
    try:
        await DraftService().schedule_publication(draft_id, when)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return BotState.SCHEDULE_DATETIME
    context.user_data.pop("schedule_draft_id", None)
    await update.effective_message.reply_text(
        f"Черновик #{draft_id} запланирован на {when:%Y-%m-%d %H:%M %Z}."
    )
    return ConversationHandler.END
