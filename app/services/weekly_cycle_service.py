from __future__ import annotations

import logging

from app.services.content_plan_service import ContentPlanService
from app.services.report_service import ReportService
from app.services.source_analysis_service import SourceAnalysisService

logger = logging.getLogger(__name__)


class WeeklyCycleService:
    def __init__(
        self,
        source_analysis: SourceAnalysisService | None = None,
        content_plan: ContentPlanService | None = None,
        report: ReportService | None = None,
    ) -> None:
        self.source_analysis = source_analysis or SourceAnalysisService()
        self.content_plan = content_plan or ContentPlanService()
        self.report = report or ReportService()

    async def run(self) -> None:
        for name, step in (
            ("competitor", self.source_analysis.generate_competitor_report),
            ("content_plan", self.content_plan.generate_weekly_plan),
            ("performance", self.report.generate_weekly_performance_report),
        ):
            try:
                await step()
            except Exception:
                logger.warning("Weekly cycle step %s failed; continuing.", name)
