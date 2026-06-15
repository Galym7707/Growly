from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.bot.i18n import SUPPORTED_LANGUAGES, tr


MAIN_MENU_ROWS = [
    ["Анализ рынка", "Контент-план"],
    ["Создать пост", "Источники"],
    ["Черновики", "Отчёты"],
    ["Ещё"],
]

SOURCES_MENU_ROWS = [
    ["Просмотреть источники"],
    ["Найти новые источники", "Проверить источники"],
    ["Назад"],
]

CREATE_POST_MENU_ROWS = [
    ["Рекламный пост", "Обучающий пост"],
    ["Пост о результате клиента", "FAQ-пост"],
    ["Новостной пост", "Instagram caption"],
    ["Свой вариант"],
    ["Назад"],
]

REPORTS_MENU_ROWS = [
    ["Последний анализ рынка"],
    ["Последний конкурентный отчёт"],
    ["Отчёт по публикациям"],
    ["Все отчёты"],
    ["Назад"],
]

SETTINGS_MENU_ROWS = [
    ["Показать настройки", "Новый бизнес"],
    ["Синхронизировать с Notion"],
    ["Язык"],
    ["Назад"],
]

TOOLS_MENU_ROWS = [
    ["Веб-поиск", "Анализ отзывов"],
    ["Настройки", "Справка"],
    ["Назад"],
]

NAVIGATION_BUTTON_LABELS = frozenset(
    label
    for rows in (
        MAIN_MENU_ROWS,
        SOURCES_MENU_ROWS,
        CREATE_POST_MENU_ROWS,
        REPORTS_MENU_ROWS,
        SETTINGS_MENU_ROWS,
        TOOLS_MENU_ROWS,
    )
    for row in rows
    for label in row
) | {
    # Keep stale keyboards and old shortcuts safe during deployments.
    "Discover sources",
    "Monitor sources",
    "Case post",
    "Create case",
    "Pending drafts",
    "More",
    "Market scan",
    "Content plan",
    "Create post",
    "Drafts",
    "Reports",
    "Sources",
    "Settings",
    "Help",
    "View sources",
    "Find new sources",
    "Check saved sources",
    "Promo post",
    "Educational post",
    "Client result post",
    "FAQ post",
    "News post",
    "Custom post",
    "View latest reports",
    "Competitor report",
    "Performance report",
    "View settings",
    "New business",
    "Tools",
    "Sync Notion",
    "Web search",
    "Review analysis",
    "Back",
} | frozenset(
    tr(label, language)
    for language in SUPPORTED_LANGUAGES
    for rows in (
        MAIN_MENU_ROWS,
        SOURCES_MENU_ROWS,
        CREATE_POST_MENU_ROWS,
        REPORTS_MENU_ROWS,
        SETTINGS_MENU_ROWS,
        TOOLS_MENU_ROWS,
    )
    for row in rows
    for label in row
)


def _translated_rows(rows: list[list[str]]) -> list[list[str]]:
    return [[tr(label) for label in row] for row in rows]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(MAIN_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def sources_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(SOURCES_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def create_post_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(CREATE_POST_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def reports_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(REPORTS_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def settings_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(SETTINGS_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def more_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        _translated_rows(TOOLS_MENU_ROWS),
        resize_keyboard=True,
        is_persistent=True,
    )


def source_actions_keyboard(sources: list[object]) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources[:30]:
        source_id = int(getattr(source, "id"))
        status = str(getattr(source, "status", ""))
        buttons: list[InlineKeyboardButton] = []
        if status != "active":
            buttons.append(
                InlineKeyboardButton(
                    tr("Подтвердить #{id}", id=source_id),
                    callback_data=f"source:approve:{source_id}",
                )
            )
        if status != "disabled":
            buttons.append(
                InlineKeyboardButton(
                    tr("Отключить #{id}", id=source_id),
                    callback_data=f"source:disable:{source_id}",
                )
            )
        if buttons:
            rows.append(buttons)
    return InlineKeyboardMarkup(rows) if rows else None


def market_scan_actions_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Конкуренты"),
                    callback_data=f"market:competitor:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Создать контент-план"),
                    callback_data=f"market:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Синхронизировать с Notion"),
                    callback_data=f"market:notion:{report_id}",
                ),
                InlineKeyboardButton(
                    tr("Новый поиск"),
                    callback_data="market:new_search",
                ),
            ],
        ]
    )


def competitor_report_actions_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Открыть полный отчёт"),
                    callback_data=f"report:view:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Создать контент-план"),
                    callback_data=f"report:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Создать пост по отчёту"),
                    callback_data=f"report:create_post:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Синхронизировать с Notion"),
                    callback_data=f"report:notion:{report_id}",
                )
            ],
        ]
    )


def report_post_type_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Рекламный пост"),
                    callback_data=f"report_post:{report_id}:promo_post",
                ),
                InlineKeyboardButton(
                    tr("Обучающий пост"),
                    callback_data=f"report_post:{report_id}:educational_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    tr("Пост о результате"),
                    callback_data=f"report_post:{report_id}:case_post",
                ),
                InlineKeyboardButton(
                    tr("FAQ-пост"),
                    callback_data=f"report_post:{report_id}:faq_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    tr("Новостной пост"),
                    callback_data=f"report_post:{report_id}:news_post",
                ),
            ],
        ]
    )


def market_scan_pending_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Повторить ИИ-анализ"),
                    callback_data=f"market:retry:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Открыть источники"),
                    callback_data=f"market:view_sources:{report_id}",
                ),
                InlineKeyboardButton(
                    tr("Синхронизировать с Notion"),
                    callback_data=f"market:notion:{report_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    tr("Создать план по доступным данным"),
                    callback_data=f"market:limited_plan:{report_id}",
                )
            ],
        ]
    )


def new_business_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Да, удалить контекст"),
                    callback_data="business_reset:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Отмена"),
                    callback_data="business_reset:cancel",
                )
            ],
        ]
    )


def approval_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(tr("Одобрить"), callback_data=f"approve:{draft_id}"),
            InlineKeyboardButton(tr("Создать заново"), callback_data=f"regenerate:{draft_id}"),
        ],
        [
            InlineKeyboardButton(tr("Редактировать"), callback_data=f"edit:{draft_id}"),
            InlineKeyboardButton(tr("Отклонить"), callback_data=f"reject:{draft_id}"),
        ],
        [
            InlineKeyboardButton(
                tr("Сохранить в Notion"),
                callback_data=f"notion:{draft_id}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def approved_keyboard(
    draft_id: int, *, telegram_publish_enabled: bool
) -> InlineKeyboardMarkup | None:
    rows = [
        [
            InlineKeyboardButton(
                tr("Сохранить в Notion"), callback_data=f"notion:{draft_id}"
            )
        ]
    ]
    if telegram_publish_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    tr("Опубликовать в Telegram"),
                    callback_data=f"publish:{draft_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    tr("Запланировать"),
                    callback_data=f"schedule:{draft_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows) if rows else None


def empty_performance_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr("Создать контент-план"),
                    callback_data="quick:content_plan",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Создать пост"),
                    callback_data="quick:create_post",
                )
            ],
            [
                InlineKeyboardButton(
                    tr("Открыть черновики"),
                    callback_data="quick:drafts",
                )
            ],
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Русский", callback_data="language:ru"),
                InlineKeyboardButton("English", callback_data="language:en"),
                InlineKeyboardButton("Қазақша", callback_data="language:kk"),
            ]
        ]
    )
