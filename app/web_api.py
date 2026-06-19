from __future__ import annotations

import asyncio
import hmac
import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from app.config import get_settings
from app.database import session_scope
from app.models import ContentPlan, Draft, Publication, Report, Source
from app.repositories.drafts_repo import DraftsRepository
from app.repositories.reports_repo import ReportsRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.sources_repo import SourcesRepository
from app.services.content_plan_service import ContentPlanService
from app.services.draft_service import DraftService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notion_service import NotionService
from app.services.report_service import ReportService
from app.services.source_analysis_service import SourceAnalysisService
from app.services.source_discovery_service import SourceDiscoveryService
from app.utils.errors import GrowlyError

router = APIRouter(prefix="/api", tags=["web"])
logger = logging.getLogger(__name__)
_market_scan_tasks: set[asyncio.Task[None]] = set()

BUSINESS_SETTING_KEYS = {
    "business_name",
    "business_niche",
    "business_region",
    "business_language",
    "business_brand_tone",
    "business_telegram_channel",
    "business_notion_root",
}

ACTIVE_CONTEXT_KEYS = {
    "active_report_id",
    "active_topic",
    "active_region",
    "active_language",
    "active_report_type",
    "active_sources_count",
    "active_created_at",
}

ACTIVE_CONTEXT_REPORT_TYPES = {"market_scan", "competitor_report", "competitor"}


def require_web_api_key(
    x_growly_api_key: str | None = Header(default=None),
) -> None:
    configured = get_settings().growly_web_api_key
    if configured is None or not configured.get_secret_value().strip():
        return
    supplied = x_growly_api_key or ""
    if not hmac.compare_digest(configured.get_secret_value(), supplied):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Growly web API key.",
        )


secured_router = APIRouter(dependencies=[Depends(require_web_api_key)])


class MarketScanRequest(BaseModel):
    niche: str = Field(min_length=2, max_length=300)
    region_language: str = Field(default="Казахстан, русский язык", max_length=300)
    competitor_keywords: str = Field(default="", max_length=500)
    language: Literal["ru", "en", "kk"] = "ru"


class CompetitorReportRequest(BaseModel):
    query: str | None = Field(default=None, max_length=500)
    language: Literal["ru", "en", "kk"] = "ru"


class ContentPlanRequest(BaseModel):
    weekly_objective: str = Field(min_length=2, max_length=1000)
    business: dict[str, Any] = Field(default_factory=dict)
    language: Literal["ru", "en", "kk"] = "ru"


class CreatePostRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=12000)
    channel: str = Field(default="Telegram", max_length=100)
    title: str | None = Field(default=None, max_length=300)
    cta: str | None = Field(default=None, max_length=1000)
    language: Literal["ru", "en", "kk"] = "ru"


class DraftActionRequest(BaseModel):
    action: Literal["approve", "reject", "regenerate", "sync_notion"]
    comment: str | None = Field(default=None, max_length=2000)
    approved_by: str | None = Field(default="Web user", max_length=300)


class DiscoverSourcesRequest(BaseModel):
    niche: str = Field(min_length=2, max_length=300)
    region: str = Field(min_length=2, max_length=300)
    platforms: list[str] = Field(min_length=1, max_length=5)


class AddSourceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    source_type: str = Field(min_length=2, max_length=100)
    url: str = Field(default="", max_length=2000)
    category: str = Field(default="competitor", max_length=100)
    priority: str = Field(default="medium", max_length=30)
    check_frequency: str = Field(default="weekly", max_length=30)


class NotionSyncRequest(BaseModel):
    target: Literal["recent", "report", "draft"] = "recent"
    target_id: int | None = Field(default=None, ge=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    action: Literal[
        "market_scan",
        "competitors",
        "content_plan",
        "create_post",
        "drafts",
        "reports",
        "sources",
        "notion_sync",
    ] | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    language: Literal["ru", "en", "kk"] = "ru"


class ActiveContextRequest(BaseModel):
    active_report_id: int | None = Field(default=None, ge=1)


class WorkspaceSettingsRequest(BaseModel):
    business_name: str | None = Field(default=None, max_length=300)
    business_niche: str | None = Field(default=None, max_length=500)
    business_region: str | None = Field(default=None, max_length=300)
    business_language: str | None = Field(default=None, max_length=100)
    business_brand_tone: str | None = Field(default=None, max_length=1000)
    business_telegram_channel: str | None = Field(default=None, max_length=300)
    business_notion_root: str | None = Field(default=None, max_length=500)


def _date_value(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _report_payload(report: Report) -> dict[str, Any]:
    return {
        "id": report.id,
        "type": report.report_type,
        "title": report.title,
        "body": report.body or report.report_text,
        "summary": report.summary,
        "query": report.query,
        "sources_count": report.sources_count,
        "evidence": report.evidence_json or [],
        "recommendations": report.recommendations_json or [],
        "structure": report.raw_json or {},
        "week_start": _date_value(report.week_start),
        "week_end": _date_value(report.week_end),
        "status": report.status,
        "notion_synced": bool(report.notion_page_id),
        "notion_url": (
            NotionService.page_url(report.notion_page_id)
            if report.notion_page_id
            else None
        ),
        "created_at": _date_value(report.created_at),
        "updated_at": _date_value(report.updated_at),
    }


def _draft_payload(draft: Draft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "content_plan_id": draft.content_plan_id,
        "type": draft.draft_type,
        "channel": draft.channel,
        "title": draft.title,
        "text": draft.draft_text,
        "version": draft.version,
        "status": draft.status,
        "approved_by": draft.approved_by,
        "metadata": draft.generation_metadata_json or {},
        "notion_synced": bool(draft.notion_page_id),
        "notion_url": (
            NotionService.page_url(draft.notion_page_id)
            if draft.notion_page_id
            else None
        ),
        "created_at": _date_value(draft.created_at),
        "updated_at": _date_value(draft.updated_at),
    }


def _source_payload(source: Source) -> dict[str, Any]:
    return {
        "id": source.id,
        "name": source.name,
        "type": source.source_type,
        "url": source.url,
        "category": source.category,
        "priority": source.priority,
        "frequency": source.check_frequency,
        "status": source.status,
        "notes": source.notes,
        "last_checked_at": _date_value(source.last_checked_at),
        "notion_synced": bool(source.notion_page_id),
        "created_at": _date_value(source.created_at),
    }


def _content_plan_payload(item: ContentPlan) -> dict[str, Any]:
    return {
        "id": item.id,
        "publish_date": _date_value(item.publish_date),
        "channel": item.channel,
        "content_type": item.content_type,
        "topic": item.topic,
        "goal": item.goal,
        "target_audience": item.target_audience,
        "key_message": item.key_message,
        "cta": item.cta,
        "source_idea": item.source_idea,
        "why_recommended": item.why_recommended,
        "status": item.status,
        "notion_synced": bool(item.notion_page_id),
        "created_at": _date_value(item.created_at),
        "updated_at": _date_value(item.updated_at),
    }


def _dashboard_data() -> dict[str, Any]:
    with session_scope() as session:
        reports = ReportsRepository(session)
        drafts = DraftsRepository(session)
        sources = SourcesRepository(session)
        latest_market = reports.latest_report("market_scan")
        latest_competitor = (
            reports.latest_report("competitor_report")
            or reports.latest_report("competitor")
        )
        latest_plan = session.scalar(
            select(ContentPlan).order_by(desc(ContentPlan.created_at)).limit(1)
        )
        pending_drafts = drafts.list_pending(limit=5)
        active_sources = sources.list_sources(active_only=True)
        notion_last_sync = SettingsRepository(session).get("notion_last_sync_at")
        published_count = int(
            session.scalar(
                select(func.count(Publication.id)).where(
                    Publication.status == "published"
                )
            )
            or 0
        )
        return {
            "workspace_mode": "single",
            "latest_market_scan": (
                _report_payload(latest_market) if latest_market else None
            ),
            "latest_competitor_report": (
                _report_payload(latest_competitor) if latest_competitor else None
            ),
            "latest_content_plan": (
                _content_plan_payload(latest_plan) if latest_plan else None
            ),
            "drafts_waiting": [_draft_payload(row) for row in pending_drafts],
            "counts": {
                "pending_drafts": len(pending_drafts),
                "active_sources": len(active_sources),
                "published": published_count,
            },
            "notion": {
                "configured": bool(
                    get_settings().notion_api_key
                    and get_settings().notion_api_key.get_secret_value().strip()
                ),
                "last_synced_at": notion_last_sync,
            },
        }


def _list_content_plan(limit: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = list(
            session.scalars(
                select(ContentPlan)
                .order_by(desc(ContentPlan.publish_date), desc(ContentPlan.id))
                .limit(limit)
            )
        )
        return [_content_plan_payload(row) for row in rows]


def _content_plan_source_payload(session: Any) -> dict[str, Any] | None:
    report = ReportsRepository(session).latest_report("market_scan")
    if report is None:
        return None
    raw = report.raw_json if isinstance(report.raw_json, dict) else {}
    market_context = (
        raw.get("market_context") if isinstance(raw.get("market_context"), dict) else {}
    )
    return {
        "report_id": report.id,
        "report_title": report.title,
        "sources_count": report.sources_count,
        "created_at": _date_value(report.created_at),
        "language": market_context.get("language"),
        "notion_synced": bool(report.notion_page_id),
        "notion_url": (
            NotionService.page_url(report.notion_page_id)
            if report.notion_page_id
            else None
        ),
    }


def _list_content_plan_response(limit: int) -> dict[str, Any]:
    with session_scope() as session:
        rows = list(
            session.scalars(
                select(ContentPlan)
                .order_by(desc(ContentPlan.publish_date), desc(ContentPlan.id))
                .limit(limit)
            )
        )
        return {
            "items": [_content_plan_payload(row) for row in rows],
            "source": _content_plan_source_payload(session),
        }


def _content_plan_detail_response(plan_id: int) -> dict[str, Any]:
    with session_scope() as session:
        anchor = session.get(ContentPlan, plan_id)
        if anchor is None:
            raise HTTPException(status_code=404, detail="Контент-план не найден.")
        rows: list[ContentPlan]
        if anchor.created_at:
            rows = list(
                session.scalars(
                    select(ContentPlan)
                    .where(
                        ContentPlan.id >= anchor.id,
                        ContentPlan.created_at
                        >= anchor.created_at - timedelta(seconds=30),
                        ContentPlan.created_at
                        <= anchor.created_at + timedelta(seconds=30),
                    )
                    .order_by(ContentPlan.publish_date, ContentPlan.id)
                )
            )
        else:
            rows = [anchor]
        if not rows:
            rows = [anchor]
        return {
            "plan_id": plan_id,
            "items": [_content_plan_payload(row) for row in rows],
            "source": _content_plan_source_payload(session),
        }


def _workspace_settings() -> dict[str, str | None]:
    with session_scope() as session:
        return SettingsRepository(session).get_many(sorted(BUSINESS_SETTING_KEYS))


def _save_workspace_settings(values: dict[str, str | None]) -> dict[str, str | None]:
    with session_scope() as session:
        repository = SettingsRepository(session)
        for key, value in values.items():
            if key in BUSINESS_SETTING_KEYS:
                repository.set(key, value.strip() if value else None)
        return repository.get_many(sorted(BUSINESS_SETTING_KEYS))


def _active_payload_from_report(
    report: Report,
    stored: dict[str, str | None],
) -> dict[str, Any]:
    raw = report.raw_json if isinstance(report.raw_json, dict) else {}
    market_context = (
        raw.get("market_context")
        if isinstance(raw.get("market_context"), dict)
        else {}
    )
    topic = (
        market_context.get("topic")
        or stored.get("active_topic")
        or report.query
        or report.title
    )
    return {
        "report_id": report.id,
        "report_title": report.title,
        "report_type": report.report_type,
        "topic": topic,
        "region": market_context.get("region") or stored.get("active_region"),
        "language": (
            market_context.get("language") or stored.get("active_language")
        ),
        "sources_count": report.sources_count,
        "created_at": _date_value(report.created_at),
        "status": report.status,
        "notion_synced": bool(report.notion_page_id),
        "notion_url": (
            NotionService.page_url(report.notion_page_id)
            if report.notion_page_id
            else None
        ),
    }


def _resolve_active_report(session: Any, stored: dict[str, str | None]) -> Report | None:
    reports = ReportsRepository(session)
    raw_id = stored.get("active_report_id")
    report = None
    if raw_id and str(raw_id).isdigit():
        report = reports.get_report(int(raw_id))
    if (
        report is None
        or report.report_type not in ACTIVE_CONTEXT_REPORT_TYPES
    ):
        report = reports.latest_report("market_scan")
    return report


def _active_context_data() -> dict[str, Any]:
    with session_scope() as session:
        stored = SettingsRepository(session).get_many(sorted(ACTIVE_CONTEXT_KEYS))
        report = _resolve_active_report(session, stored)
        if report is None:
            return {"active": None}
        return {"active": _active_payload_from_report(report, stored)}


def _set_active_context(report_id: int | None) -> dict[str, Any]:
    with session_scope() as session:
        settings_repo = SettingsRepository(session)
        if report_id is None:
            for key in ACTIVE_CONTEXT_KEYS:
                settings_repo.set(key, None)
            return {"active": None}
        report = ReportsRepository(session).get_report(report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Отчёт не найден.")
        payload = _active_payload_from_report(report, {})
        settings_repo.set("active_report_id", str(payload["report_id"]))
        settings_repo.set("active_topic", payload["topic"])
        settings_repo.set("active_region", payload["region"])
        settings_repo.set("active_language", payload["language"])
        settings_repo.set("active_report_type", payload["report_type"])
        settings_repo.set("active_sources_count", str(payload["sources_count"]))
        settings_repo.set("active_created_at", payload["created_at"])
        return {"active": payload}


def _infer_chat_action(message: str) -> str | None:
    normalized = message.strip().lower()
    patterns = (
        ("market_scan", ("анализ рынка", "рынок", "market scan")),
        ("competitors", ("конкурент", "competitor")),
        ("content_plan", ("контент-план", "контент план", "content plan")),
        ("create_post", ("создать пост", "напиши пост", "create post")),
        ("drafts", ("черновик", "draft")),
        ("reports", ("отчёт", "отчет", "report")),
        ("sources", ("источник", "source")),
        ("notion_sync", ("notion", "синхронизац")),
    )
    for action, keywords in patterns:
        if any(keyword in normalized for keyword in keywords):
            return action
    return None


@secured_router.get("/dashboard")
async def dashboard() -> dict[str, Any]:
    return await asyncio.to_thread(_dashboard_data)


@secured_router.get("/health")
async def web_health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": get_settings().app_name,
        "environment": get_settings().environment,
    }


async def _run_market_scan_sync(payload: MarketScanRequest) -> dict[str, Any]:
    report, sources = await MarketIntelligenceService().run_market_scan(
        niche=payload.niche,
        region_language=payload.region_language,
        competitor_keywords=payload.competitor_keywords,
        output_language=payload.language,
    )
    report_payload = _report_payload(report)
    return {
        "status": "completed",
        "message": "Отчёт готов",
        "report_id": report.id,
        "sources_count": len(sources),
        "report": report_payload,
        "sources_saved": len(sources),
    }


async def _run_market_scan_job(
    service: MarketIntelligenceService,
    job_id: int,
    payload: MarketScanRequest,
) -> None:
    try:
        await service.run_market_scan(
            niche=payload.niche,
            region_language=payload.region_language,
            competitor_keywords=payload.competitor_keywords,
            job_id=job_id,
            output_language=payload.language,
        )
    except asyncio.CancelledError:
        await service.cancel_market_scan_job(job_id)
        raise
    except Exception as exc:
        safe_error = (
            str(exc)
            if isinstance(exc, GrowlyError)
            else f"Unexpected {type(exc).__name__}"
        )
        await service.fail_market_scan_job(job_id, safe_error)
        logger.exception(
            "Web market scan job %s failed: %s",
            job_id,
            type(exc).__name__,
        )


def _schedule_market_scan_job(
    service: MarketIntelligenceService,
    job_id: int,
    payload: MarketScanRequest,
) -> None:
    task = asyncio.create_task(_run_market_scan_job(service, job_id, payload))
    _market_scan_tasks.add(task)
    task.add_done_callback(_market_scan_tasks.discard)


@secured_router.post(
    "/market-scan",
    status_code=status.HTTP_202_ACCEPTED,
)
async def market_scan(payload: MarketScanRequest) -> dict[str, Any]:
    service = MarketIntelligenceService()
    job = await service.create_market_scan_job(None, payload.niche)
    _schedule_market_scan_job(service, job.id, payload)
    return {
        "status": "accepted",
        "message": "Анализ рынка запущен",
        "job_id": job.id,
        "current_step": job.current_step,
        "sources_count": job.sources_count,
    }


@secured_router.get("/market-scan/jobs/{job_id}")
async def market_scan_job(job_id: int) -> dict[str, Any]:
    job = await MarketIntelligenceService().market_scan_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание анализа рынка не найдено.",
        )
    return {
        "status": job["status"],
        "message": job["current_step"],
        "job_id": job["id"],
        "current_step": job["current_step"],
        "sources_count": job["sources_count"],
        "sources_saved": job["sources_count"],
        "report_id": job["report_id"],
        "report_status": job["report_status"],
        "error_message": job["error_message"],
    }


@secured_router.post("/competitor-report")
async def competitor_report(payload: CompetitorReportRequest) -> dict[str, Any]:
    report = await MarketIntelligenceService().generate_competitor_report(
        query=payload.query,
        output_language=payload.language,
    )
    return {
        "status": "completed",
        "message": "Отчёт готов",
        "report_id": report.id,
        "sources_count": report.sources_count,
        "report": _report_payload(report),
    }


@secured_router.get("/content-plan")
async def content_plan_list(
    limit: int = Query(default=40, ge=1, le=200),
) -> dict[str, Any]:
    return await asyncio.to_thread(_list_content_plan_response, limit)


@secured_router.get("/content-plans")
async def content_plans_list(
    limit: int = Query(default=40, ge=1, le=200),
) -> dict[str, Any]:
    return await content_plan_list(limit=limit)


@secured_router.get("/content-plans/{plan_id}")
async def content_plan_detail(plan_id: int) -> dict[str, Any]:
    return await asyncio.to_thread(_content_plan_detail_response, plan_id)


@secured_router.post("/content-plan")
async def content_plan_create(payload: ContentPlanRequest) -> dict[str, Any]:
    items = await ContentPlanService().generate_weekly_plan(
        {
            "weekly_objective": payload.weekly_objective,
            "business": {**payload.business, "language": payload.language},
            "language": payload.language,
        }
    )
    plan_id = items[0].id if items else None
    return {
        "status": "completed",
        "plan_id": plan_id,
        "content_plan_id": plan_id,
        "items": [_content_plan_payload(item) for item in items],
    }


@secured_router.post("/content-plans")
async def content_plans_create(payload: ContentPlanRequest) -> dict[str, Any]:
    return await content_plan_create(payload)


@secured_router.post("/content-plan/{item_id}/draft")
async def content_plan_draft(item_id: int) -> dict[str, Any]:
    draft = await DraftService().create_from_plan(item_id)
    return {
        "status": "completed",
        "draft_id": draft.id,
        "draft": _draft_payload(draft),
    }


@secured_router.post("/create-post")
async def create_post(payload: CreatePostRequest) -> dict[str, Any]:
    draft = await DraftService().create_post(payload.model_dump(exclude_none=True))
    return {
        "status": "completed",
        "draft_id": draft.id,
        "draft": _draft_payload(draft),
    }


@secured_router.get("/drafts")
async def drafts(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    def load() -> list[Draft]:
        with session_scope() as session:
            return DraftsRepository(session).list_recent(limit)

    rows = await asyncio.to_thread(load)
    return {"items": [_draft_payload(row) for row in rows]}


@secured_router.patch("/drafts/{draft_id}")
async def update_draft(
    draft_id: int,
    payload: DraftActionRequest,
) -> dict[str, Any]:
    service = DraftService()
    if payload.action == "regenerate":
        draft = await service.regenerate(draft_id)
    elif payload.action == "sync_notion":
        await service.ensure_notion(draft_id)
        draft = await service.get(draft_id)
    else:
        draft = await service.record_action(
            draft_id=draft_id,
            telegram_chat_id="web",
            action=payload.action,
            approved_by=payload.approved_by,
            comment=payload.comment,
        )
    if draft is None:
        raise HTTPException(status_code=404, detail="Черновик не найден.")
    return {"status": "completed", "draft": _draft_payload(draft)}


@secured_router.get("/reports")
async def reports(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    rows = await ReportService().list_latest(limit)
    return {"items": [_report_payload(row) for row in rows]}


@secured_router.get("/reports/{report_id}")
async def report(report_id: int) -> dict[str, Any]:
    row = await ReportService().get_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден.")
    return {"report": _report_payload(row)}


@secured_router.get("/sources")
async def sources(
    active_only: bool = Query(default=False),
) -> dict[str, Any]:
    rows = await SourceAnalysisService().list_sources(active_only=active_only)
    return {"items": [_source_payload(row) for row in rows]}


@secured_router.post("/sources")
async def add_source(payload: AddSourceRequest) -> dict[str, Any]:
    source = await SourceAnalysisService().add_source(**payload.model_dump())
    return {"status": "completed", "source": _source_payload(source)}


@secured_router.post("/sources/discover")
async def discover_sources(payload: DiscoverSourcesRequest) -> dict[str, Any]:
    rows = await SourceDiscoveryService().discover_sources(**payload.model_dump())
    return {
        "status": "completed",
        "items": [_source_payload(row) for row in rows],
    }


@secured_router.post("/sources/monitor")
async def monitor_sources() -> dict[str, Any]:
    report_row, items = await SourceDiscoveryService().monitor_active_sources()
    return {
        "status": "completed",
        "report": _report_payload(report_row),
        "items_saved": len(items),
    }


@secured_router.post("/notion/sync")
async def notion_sync(payload: NotionSyncRequest) -> dict[str, Any]:
    if payload.target == "report":
        if payload.target_id is None:
            raise HTTPException(status_code=422, detail="Укажите ID отчёта.")
        url = await ReportService().sync_report_to_notion(payload.target_id)
        return {"status": "completed", "target": "report", "url": url}
    if payload.target == "draft":
        if payload.target_id is None:
            raise HTTPException(status_code=422, detail="Укажите ID черновика.")
        url = await DraftService().ensure_notion(payload.target_id)
        return {"status": "completed", "target": "draft", "url": url}
    counts = await NotionService().sync_recent_data()
    return {"status": "completed", "target": "recent", "counts": counts}


@secured_router.get("/context/active")
async def active_context() -> dict[str, Any]:
    return await asyncio.to_thread(_active_context_data)


@secured_router.patch("/context/active")
async def update_active_context(payload: ActiveContextRequest) -> dict[str, Any]:
    return await asyncio.to_thread(_set_active_context, payload.active_report_id)


@secured_router.get("/settings")
async def settings() -> dict[str, Any]:
    return {
        "workspace_mode": "single",
        "settings": await asyncio.to_thread(_workspace_settings),
    }


@secured_router.patch("/settings")
async def update_settings(payload: WorkspaceSettingsRequest) -> dict[str, Any]:
    values = payload.model_dump()
    saved = await asyncio.to_thread(_save_workspace_settings, values)
    return {"status": "completed", "settings": saved}


@secured_router.post("/chat")
async def chat(payload: ChatRequest) -> dict[str, Any]:
    action = payload.action or _infer_chat_action(payload.message)
    context = payload.context
    if action == "market_scan":
        request = MarketScanRequest(
            niche=str(context.get("niche") or payload.message),
            region_language=str(
                context.get("region_language") or "Казахстан, русский язык"
            ),
            competitor_keywords=str(context.get("competitor_keywords") or ""),
            language=payload.language,
        )
        result = await _run_market_scan_sync(request)
    elif action == "competitors":
        result = await competitor_report(
            CompetitorReportRequest(
                query=str(context.get("query") or payload.message),
                language=payload.language,
            )
        )
    elif action == "content_plan":
        result = await content_plan_create(
            ContentPlanRequest(
                weekly_objective=str(
                    context.get("weekly_objective") or payload.message
                ),
                business=(
                    {
                        **context.get("business"),
                        "language": payload.language,
                    }
                    if isinstance(context.get("business"), dict)
                    else {"language": payload.language}
                ),
                language=payload.language,
            )
        )
    elif action == "create_post":
        result = await create_post(
            CreatePostRequest(
                brief=str(context.get("brief") or payload.message),
                channel=str(context.get("channel") or "Telegram"),
                title=(
                    str(context["title"]) if context.get("title") else None
                ),
                cta=str(context["cta"]) if context.get("cta") else None,
                language=payload.language,
            )
        )
    elif action == "drafts":
        result = await drafts(limit=50)
    elif action == "reports":
        result = await reports(limit=50)
    elif action == "sources":
        result = await sources(active_only=False)
    elif action == "notion_sync":
        result = await notion_sync(NotionSyncRequest())
    else:
        return {
            "status": "needs_action",
            "message": (
                "Уточните действие: анализ рынка, конкуренты, контент-план, "
                "создание поста, черновики, отчёты, источники или синхронизация Notion."
            ),
            "available_actions": [
                "market_scan",
                "competitors",
                "content_plan",
                "create_post",
                "drafts",
                "reports",
                "sources",
                "notion_sync",
            ],
        }
    return {
        "status": "completed",
        "action": action,
        "message": "Задача выполнена.",
        "result": result,
    }


router.include_router(secured_router)
