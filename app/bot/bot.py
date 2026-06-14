from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot import handlers
from app.bot.states import BotState
from app.config import Settings, get_settings
from app.runtime_status import telegram_initialized
from app.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


def build_application(settings: Settings | None = None) -> Application:
    settings = settings or get_settings()
    scheduler = SchedulerService(settings)

    async def post_init(application: Application) -> None:
        await handlers.register_commands(application)
        scheduler.start_if_enabled()
        telegram_initialized.set()
        logger.info("telegram_bot_initialized")

    async def post_shutdown(application: Application) -> None:
        telegram_initialized.clear()
        scheduler.shutdown()

    application = (
        ApplicationBuilder()
        .token(settings.telegram_token())
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    private_chat = filters.ChatType.PRIVATE

    def conversation_fallbacks() -> list[CommandHandler]:
        return [
            CommandHandler("cancel", handlers.cancel, filters=private_chat),
            CommandHandler(
                "new_business",
                handlers.new_business_start,
                filters=private_chat,
            ),
        ]

    application.add_handler(
        CommandHandler("start", handlers.start, filters=private_chat)
    )
    application.add_handler(
        CommandHandler("help", handlers.help_command, filters=private_chat)
    )
    application.add_handler(
        CommandHandler(
            "create_post",
            handlers.create_post_menu,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler("drafts", handlers.drafts, filters=private_chat)
    )
    application.add_handler(
        CommandHandler("reports", handlers.reports, filters=private_chat)
    )
    application.add_handler(
        CommandHandler("sources", handlers.sources, filters=private_chat)
    )
    application.add_handler(
        CommandHandler(
            "monitor_sources",
            handlers.monitor_sources,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "performance_report",
            handlers.performance_report,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "sync_notion",
            handlers.sync_notion,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "retry_analysis",
            handlers.retry_analysis,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "status",
            handlers.task_status,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "debug_notion_status",
            handlers.debug_notion_status,
            filters=private_chat,
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "discover_sources",
                    handlers.discover_sources_start,
                    filters=private_chat,
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Discover sources$"),
                    handlers.discover_sources_start,
                ),
            ],
            states={
                BotState.DISCOVER_SOURCES_NICHE: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.discover_sources_niche,
                    )
                ],
                BotState.DISCOVER_SOURCES_REGION: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.discover_sources_region,
                    )
                ],
                BotState.DISCOVER_SOURCES_PLATFORMS: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.discover_sources_finish,
                    )
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "web_search", handlers.web_search_start, filters=private_chat
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Web search$"),
                    handlers.web_search_start,
                ),
                CallbackQueryHandler(
                    handlers.web_search_start,
                    pattern=r"^market:new_search$",
                ),
            ],
            states={
                BotState.WEB_SEARCH_QUERY: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.web_search_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "market_scan", handlers.market_scan_start, filters=private_chat
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Market scan$"),
                    handlers.market_scan_start,
                ),
            ],
            states={
                BotState.MARKET_SCAN_NICHE: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.market_scan_niche,
                    )
                ],
                BotState.MARKET_SCAN_REGION: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.market_scan_region,
                    )
                ],
                BotState.MARKET_SCAN_COMPETITORS: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.market_scan_finish,
                    )
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "competitor_report",
                    handlers.competitor_report,
                    filters=private_chat,
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^(Competitor report|Generate competitor report)$"),
                    handlers.competitor_report,
                ),
            ],
            states={
                BotState.COMPETITOR_REPORT_TOPIC: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.competitor_report_topic,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                MessageHandler(
                    private_chat
                    & filters.Regex(
                        r"^(Promo post|Educational post|Case post|FAQ post|"
                        r"News post|Custom post|Create one-off post)$"
                    ),
                    handlers.create_post_type_start,
                ),
            ],
            states={
                BotState.WAITING_POST: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.create_post_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("add_source", handlers.add_source_start, filters=private_chat),
                MessageHandler(
                    private_chat & filters.Regex(r"^Add source$"),
                    handlers.add_source_start,
                ),
            ],
            states={
                BotState.ADD_SOURCE_NAME: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_name)
                ],
                BotState.ADD_SOURCE_TYPE: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_type)
                ],
                BotState.ADD_SOURCE_URL: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_url)
                ],
                BotState.ADD_SOURCE_CATEGORY: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_category)
                ],
                BotState.ADD_SOURCE_PRIORITY: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_priority)
                ],
                BotState.ADD_SOURCE_FREQUENCY: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.add_source_finish)
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "disable_source", handlers.disable_source_start, filters=private_chat
                )
            ],
            states={
                BotState.DISABLE_SOURCE: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.disable_source_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "import_source_items", handlers.import_source_start, filters=private_chat
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Import competitor posts$"),
                    handlers.import_source_start,
                ),
            ],
            states={
                BotState.IMPORT_SOURCE_SELECT: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.import_source_select,
                    )
                ],
                BotState.IMPORT_SOURCE_TEXT: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.import_source_finish,
                    )
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("content_plan", handlers.content_plan_start, filters=private_chat),
                MessageHandler(
                    private_chat & filters.Regex(r"^(Content plan|Generate content plan)$"),
                    handlers.content_plan_start,
                ),
            ],
            states={
                BotState.PLAN_GOAL: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.content_plan_goal)
                ],
                BotState.PLAN_AUDIENCE: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.content_plan_audience)
                ],
                BotState.PLAN_OFFER: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.content_plan_offer)
                ],
                BotState.PLAN_CHANNELS: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.content_plan_channels)
                ],
                BotState.PLAN_INTENSITY: [
                    MessageHandler(private_chat & filters.TEXT & ~filters.COMMAND, handlers.content_plan_finish)
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "generate_from_plan", handlers.generate_from_plan_start, filters=private_chat
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Generate draft from plan$"),
                    handlers.generate_from_plan_start,
                ),
            ],
            states={
                BotState.PLAN_ITEM_SELECT: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.generate_from_plan_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "update_publication_metrics", handlers.update_metrics_start, filters=private_chat
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Update metrics$"),
                    handlers.update_metrics_start,
                ),
            ],
            states={
                BotState.METRICS_PUBLICATION_SELECT: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.update_metrics_select,
                    )
                ],
                BotState.METRICS_VALUES: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.update_metrics_finish,
                    )
                ],
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "create_case",
                    handlers.create_case_start,
                    filters=private_chat,
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Create case$"),
                    handlers.create_case_start,
                ),
            ],
            states={
                BotState.WAITING_CASE: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.create_case_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "review_analysis",
                    handlers.review_start,
                    filters=private_chat,
                ),
                MessageHandler(
                    private_chat & filters.Regex(r"^Review analysis$"),
                    handlers.review_start,
                ),
            ],
            states={
                BotState.WAITING_REVIEWS: [
                    MessageHandler(
                        private_chat & filters.TEXT & ~filters.COMMAND,
                        handlers.review_finish,
                    )
                ]
            },
            fallbacks=conversation_fallbacks(),
        )
    )

    application.add_handler(
        CommandHandler(
            "new_business",
            handlers.new_business_start,
            filters=private_chat,
        )
    )
    application.add_handler(
        CommandHandler(
            "cancel",
            handlers.cancel,
            filters=private_chat,
        )
    )

    button_handlers = {
        "Create post": handlers.create_post_menu,
        "Sources": handlers.sources_menu,
        "View sources": handlers.sources,
        "Monitor sources": handlers.monitor_sources,
        "Drafts": handlers.drafts,
        "Pending drafts": handlers.drafts,
        "Reports": handlers.reports,
        "More": handlers.more_menu,
        "Performance report": handlers.performance_report,
        "Sync Notion": handlers.sync_notion,
        "Settings": handlers.settings_status,
        "Help": handlers.help_command,
        "Back": handlers.main_menu,
    }
    for label, callback in button_handlers.items():
        application.add_handler(
            MessageHandler(
                private_chat & filters.Regex(f"^{label}$"),
                callback,
            )
        )

    application.add_handler(
        CallbackQueryHandler(
            handlers.source_action_callback,
            pattern=r"^source:(approve|disable):\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handlers.new_business_callback,
            pattern=r"^business_reset:(confirm|cancel)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handlers.market_scan_action_callback,
            pattern=r"^market:(competitor|content_plan|limited_plan|notion|retry|view_sources):\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handlers.approval_callback,
            pattern=r"^(approve|regenerate|reject|notion|publish):\d+$",
        )
    )
    application.add_error_handler(handlers.error_handler)
    return application


def run_bot() -> None:
    build_application().run_polling(
        timeout=30,
        bootstrap_retries=-1,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )
