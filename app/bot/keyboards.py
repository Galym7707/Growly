from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


MAIN_MENU_ROWS = [
    ["Market scan", "Content plan"],
    ["Create post", "Drafts"],
    ["Reports", "Sources"],
    ["Settings", "Help"],
]

SOURCES_MENU_ROWS = [
    ["View sources"],
    ["Find new sources", "Check saved sources"],
    ["Back"],
]

CREATE_POST_MENU_ROWS = [
    ["Promo post", "Educational post"],
    ["Client result post", "FAQ post"],
    ["News post", "Custom post"],
    ["Back"],
]

REPORTS_MENU_ROWS = [
    ["View latest reports"],
    ["Competitor report", "Performance report"],
    ["Back"],
]

SETTINGS_MENU_ROWS = [
    ["View settings", "New business"],
    ["Tools", "Sync Notion"],
    ["Back"],
]

TOOLS_MENU_ROWS = [
    ["Web search", "Review analysis"],
    ["Back"],
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
                    f"Approve #{source_id}",
                    callback_data=f"source:approve:{source_id}",
                )
            )
        if status != "disabled":
            buttons.append(
                InlineKeyboardButton(
                    f"Disable #{source_id}",
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
                    "Competitor report",
                    callback_data=f"market:competitor:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Generate Content Plan",
                    callback_data=f"market:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Save to Notion",
                    callback_data=f"market:notion:{report_id}",
                ),
                InlineKeyboardButton(
                    "New Search",
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
                    "View full report",
                    callback_data=f"report:view:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Generate content plan",
                    callback_data=f"report:content_plan:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Create post from report",
                    callback_data=f"report:create_post:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Sync Notion",
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
                    "Promo post",
                    callback_data=f"report_post:{report_id}:promo_post",
                ),
                InlineKeyboardButton(
                    "Educational post",
                    callback_data=f"report_post:{report_id}:educational_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Client result post",
                    callback_data=f"report_post:{report_id}:case_post",
                ),
                InlineKeyboardButton(
                    "FAQ post",
                    callback_data=f"report_post:{report_id}:faq_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    "News post",
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
                    "Retry AI analysis",
                    callback_data=f"market:retry:{report_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "View sources",
                    callback_data=f"market:view_sources:{report_id}",
                ),
                InlineKeyboardButton(
                    "Sync Notion",
                    callback_data=f"market:notion:{report_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Generate content plan from limited data",
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
            InlineKeyboardButton("Approve", callback_data=f"approve:{draft_id}"),
            InlineKeyboardButton("Regenerate", callback_data=f"regenerate:{draft_id}"),
        ],
        [
            InlineKeyboardButton("Reject", callback_data=f"reject:{draft_id}"),
            InlineKeyboardButton("Save to Notion", callback_data=f"notion:{draft_id}"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def approved_keyboard(
    draft_id: int, *, telegram_publish_enabled: bool
) -> InlineKeyboardMarkup | None:
    rows = [
        [
            InlineKeyboardButton(
                "Save to Notion", callback_data=f"notion:{draft_id}"
            )
        ]
    ]
    if telegram_publish_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    "Publish to Telegram Group",
                    callback_data=f"publish:{draft_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows) if rows else None
