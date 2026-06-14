from types import SimpleNamespace

from app.services.scheduler_service import SchedulerService


def test_configure_registers_one_weekly_cycle_job() -> None:
    settings = SimpleNamespace(
        timezone="Asia/Almaty",
        weekly_report_day="monday",
        weekly_report_hour=9,
        weekly_report_minute=0,
        scheduler_enabled=True,
        telegram_token=lambda: "1:x",
    )
    svc = SchedulerService(settings)
    svc.configure()
    job_ids = {job.id for job in svc.scheduler.get_jobs()}
    assert "weekly_cycle" in job_ids
    assert "weekly_competitor_report" not in job_ids
    assert "dispatch_scheduled_publications" in job_ids
