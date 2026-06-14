from __future__ import annotations

from telegram import Bot, InlineKeyboardMarkup

from app.config import Settings, get_settings
from app.models import Draft
from app.utils.text import split_telegram_text


class TelegramService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send_long_text(
        self,
        bot: Bot,
        chat_id: int | str,
        text: str,
        *,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> int | None:
        message_ids = await self.send_text_chunks(
            bot,
            chat_id,
            text,
            reply_markup=reply_markup,
        )
        return message_ids[-1] if message_ids else None

    async def send_text_chunks(
        self,
        bot: Bot,
        chat_id: int | str,
        text: str,
        *,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> list[int]:
        message_ids: list[int] = []
        chunks = split_telegram_text(text)
        for index, chunk in enumerate(chunks):
            message = await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                reply_markup=reply_markup if index == len(chunks) - 1 else None,
                disable_web_page_preview=True,
            )
            message_ids.append(message.message_id)
        return message_ids

    async def publish_to_group(self, bot: Bot, draft: Draft) -> list[int]:
        publish_chat_id = self.settings.telegram_publish_target()
        if not publish_chat_id:
            raise ValueError(
                "TELEGRAM_PUBLISH_CHAT_ID or TELEGRAM_CHANNEL_ID is not configured."
            )
        message_ids = await self.send_text_chunks(
            bot,
            publish_chat_id,
            draft.draft_text,
        )
        if not message_ids:
            raise RuntimeError("Telegram did not return publication message IDs.")
        return message_ids
