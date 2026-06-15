from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from telegram import Bot

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import Draft, Publication
from app.repositories.reports_repo import ReportsRepository
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class PublishingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _load_due(self, now: datetime) -> list[Publication]:
        with session_scope() as session:
            rows = ReportsRepository(session).list_due_scheduled(now)
            session.expunge_all()
            return rows

    async def _publish_one(self, bot: Bot, publication: Publication) -> bool:
        def load_draft() -> Draft | None:
            with session_scope() as session:
                return session.get(Draft, publication.draft_id)

        draft = await asyncio.to_thread(load_draft)
        if draft is None:
            return False
        results = await TelegramService(self.settings).publish_to_targets(bot, draft)
        message_ids = [mid for ids in results.values() for mid in ids]

        def complete() -> None:
            with session_scope() as session:
                pub = session.get(Publication, publication.id)
                draft_row = session.get(Draft, publication.draft_id)
                if pub is None or draft_row is None:
                    return
                pub.status = "published"
                pub.published_at = datetime.now(UTC)
                pub.telegram_message_id = ",".join(map(str, message_ids))
                pub.metrics_json = {"telegram_message_ids": message_ids}
                draft_row.status = "published"

        await asyncio.to_thread(complete)
        return True

    async def dispatch_due(self, bot: Bot) -> int:
        due = self._load_due(datetime.now(UTC))
        published = 0
        for publication in due:
            try:
                if await self._publish_one(bot, publication):
                    published += 1
            except Exception:
                logger.warning(
                    "Scheduled publication %s failed; will retry next tick.",
                    publication.id,
                )
        return published
