from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings, get_settings
from app.services.content_plan_service import ContentPlanService
from app.services.report_service import ReportService
from app.services.source_analysis_service import SourceAnalysisService

logger = logging.getLogger(__name__)

DAY_ALIASES = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
}


class SchedulerService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.settings.timezone)

    def configure(self) -> None:
        day = DAY_ALIASES.get(
            self.settings.weekly_report_day.lower(),
            self.settings.weekly_report_day.lower()[:3],
        )
        trigger = CronTrigger(
            day_of_week=day,
            hour=self.settings.weekly_report_hour,
            minute=self.settings.weekly_report_minute,
            timezone=self.settings.timezone,
        )
        self.scheduler.add_job(
            SourceAnalysisService().generate_competitor_report,
            trigger=trigger,
            id="weekly_competitor_report",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            ContentPlanService().generate_weekly_plan,
            trigger=trigger,
            id="weekly_content_plan",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            ReportService().generate_weekly_performance_report,
            trigger=trigger,
            id="weekly_performance_report",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._add_publish_dispatcher()

    def _add_publish_dispatcher(self) -> None:
        from telegram import Bot
        from app.services.publishing_service import PublishingService

        async def _dispatch_scheduled() -> None:
            token = self.settings.telegram_token()
            await PublishingService(self.settings).dispatch_due(Bot(token))

        self.scheduler.add_job(
            _dispatch_scheduled,
            trigger="interval",
            minutes=1,
            id="dispatch_scheduled_publications",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def start_if_enabled(self) -> bool:
        if not self.settings.scheduler_enabled:
            logger.info("Scheduler is disabled by configuration.")
            return False
        self.configure()
        self.scheduler.start()
        logger.info("Weekly scheduler started.")
        return True

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

