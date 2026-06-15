from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


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
}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        MAIN_MENU_ROWS,
        resize_keyboard=True,
        is_persistent=True,
    )


def sources_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        SOURCES_MENU_ROWS,
        resize_keyboard=True,
        is_persistent=True,
    )


def create_post_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        CREATE_POST_MENU_ROWS,
        resize_keyboard=True,
        is_persistent=True,
    )


def reports_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        REPORTS_MENU_ROWS,
        resize_keyboard=True,
        is_persistent=True,
    )


def settings_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        SETTINGS_MENU_ROWS,
        resize_keyboard=True,
        is_persistent=True,
    )


def more_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        TOOLS_MENU_ROWS,
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
                    f"Подтвердить #{source_id}",
                    callback_data=f"source:approve:{source_id}",
                )
            )
        if status != "disabled":
            buttons.append(
                InlineKeyboardButton(
                    f"Отключить #{source_id}",
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
                    "Конкуренты",
                    callback_data=f"market:competitor:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Создать контент-план",
                    callback_data=f"market:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Синхронизировать с Notion",
                    callback_data=f"market:notion:{report_id}",
                ),
                InlineKeyboardButton(
                    "Новый поиск",
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
                    "Открыть полный отчёт",
                    callback_data=f"report:view:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Создать контент-план",
                    callback_data=f"report:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Создать пост по отчёту",
                    callback_data=f"report:create_post:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Синхронизировать с Notion",
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
                    "Рекламный пост",
                    callback_data=f"report_post:{report_id}:promo_post",
                ),
                InlineKeyboardButton(
                    "Обучающий пост",
                    callback_data=f"report_post:{report_id}:educational_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Пост о результате",
                    callback_data=f"report_post:{report_id}:case_post",
                ),
                InlineKeyboardButton(
                    "FAQ-пост",
                    callback_data=f"report_post:{report_id}:faq_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Новостной пост",
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
                    "Повторить ИИ-анализ",
                    callback_data=f"market:retry:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Открыть источники",
                    callback_data=f"market:view_sources:{report_id}",
                ),
                InlineKeyboardButton(
                    "Синхронизировать с Notion",
                    callback_data=f"market:notion:{report_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Создать план по доступным данным",
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
                    "Да, удалить контекст",
                    callback_data="business_reset:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    "Отмена",
                    callback_data="business_reset:cancel",
                )
            ],
        ]
    )


def approval_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Одобрить", callback_data=f"approve:{draft_id}"),
            InlineKeyboardButton("Создать заново", callback_data=f"regenerate:{draft_id}"),
        ],
        [
            InlineKeyboardButton("Редактировать", callback_data=f"edit:{draft_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject:{draft_id}"),
        ],
        [
            InlineKeyboardButton(
                "Сохранить в Notion",
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
                "Сохранить в Notion", callback_data=f"notion:{draft_id}"
            )
        ]
    ]
    if telegram_publish_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    "Опубликовать в Telegram",
                    callback_data=f"publish:{draft_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    "Запланировать",
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
                    "Создать контент-план",
                    callback_data="quick:content_plan",
                )
            ],
            [
                InlineKeyboardButton(
                    "Создать пост",
                    callback_data="quick:create_post",
                )
            ],
            [
                InlineKeyboardButton(
                    "Открыть черновики",
                    callback_data="quick:drafts",
                )
            ],
        ]
    )
