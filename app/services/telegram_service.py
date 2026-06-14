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

    def publish_targets(self) -> list[str]:
        targets: list[str] = []
        channel = (self.settings.telegram_channel_id or "").strip()
        group = (self.settings.telegram_publish_chat_id or "").strip()
        if getattr(self.settings, "publish_to_channel", False) and channel:
            targets.append(channel)
        if getattr(self.settings, "publish_to_group", False) and group:
            targets.append(group)
        any_flag_enabled = bool(
            getattr(self.settings, "publish_to_channel", False)
            or getattr(self.settings, "publish_to_group", False)
        )
        if not targets and any_flag_enabled:
            fallback = self.settings.telegram_publish_target()
            if fallback:
                targets.append(fallback)
        seen: set[str] = set()
        return [t for t in targets if not (t in seen or seen.add(t))]

    async def publish_to_targets(self, bot: Bot, draft: Draft) -> dict[str, list[int]]:
        targets = self.publish_targets()
        if not targets:
            raise ValueError(
                "No publish destination configured. Set PUBLISH_TO_CHANNEL/"
                "PUBLISH_TO_GROUP with TELEGRAM_CHANNEL_ID/TELEGRAM_PUBLISH_CHAT_ID."
            )
        results: dict[str, list[int]] = {}
        for chat_id in targets:
            results[chat_id] = await self.send_text_chunks(bot, chat_id, draft.draft_text)
        return results
