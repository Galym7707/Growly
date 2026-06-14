from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import MarketScanJob


class MarketScanJobsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: int | None, query: str) -> MarketScanJob:
        job = MarketScanJob(
            user_id=user_id,
            status="running",
            current_step="Шаг 1/5: ищу источники через Tavily...",
            query=query,
            sources_count=0,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> MarketScanJob | None:
        return self.session.get(MarketScanJob, job_id)

    def latest_for_user(self, user_id: int) -> MarketScanJob | None:
        return self.session.scalar(
            select(MarketScanJob)
            .where(MarketScanJob.user_id == user_id)
            .order_by(desc(MarketScanJob.created_at), desc(MarketScanJob.id))
            .limit(1)
        )

    def latest_running_for_user(self, user_id: int) -> MarketScanJob | None:
        return self.session.scalar(
            select(MarketScanJob)
            .where(
                MarketScanJob.user_id == user_id,
                MarketScanJob.status.in_(("running", "analysis_pending")),
            )
            .order_by(desc(MarketScanJob.created_at), desc(MarketScanJob.id))
            .limit(1)
        )

    def latest_for_report(self, report_id: int) -> MarketScanJob | None:
        return self.session.scalar(
            select(MarketScanJob)
            .where(MarketScanJob.report_id == report_id)
            .order_by(desc(MarketScanJob.created_at), desc(MarketScanJob.id))
            .limit(1)
        )

    def update(
        self,
        job: MarketScanJob,
        *,
        status: str | None = None,
        current_step: str | None = None,
        sources_count: int | None = None,
        report_id: int | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
    ) -> MarketScanJob:
        if status is not None:
            job.status = status
        if current_step is not None:
            job.current_step = current_step
        if sources_count is not None:
            job.sources_count = sources_count
        if report_id is not None:
            job.report_id = report_id
        if clear_error:
            job.error_message = None
        elif error_message is not None:
            job.error_message = error_message[:2000]
        self.session.flush()
        return job
