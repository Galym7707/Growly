from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["Market scan", "Content plan"],
            ["Create post", "Sources"],
            ["Drafts", "Reports"],
            ["More"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def sources_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["View sources"],
            ["Discover sources", "Monitor sources"],
            ["Back"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def create_post_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["Promo post", "Educational post"],
            ["Case post", "FAQ post"],
            ["News post", "Custom post"],
            ["Back"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def more_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["Web search", "Review analysis"],
            ["Sync Notion", "Settings"],
            ["Help"],
            ["Back"],
        ],
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
                    "Generate Competitor Report",
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
