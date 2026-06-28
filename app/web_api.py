from __future__ import annotations

import asyncio
import hmac
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select

from app.config import get_settings
from app.database import session_scope
from app.models import ContentPlan, Draft, Publication, Report, Source
from app.repositories.drafts_repo import DraftsRepository
from app.repositories.reports_repo import ReportsRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.sources_repo import SourcesRepository
from app.repositories.tasks_repo import TasksRepository
from app.repositories.workspace_repo import WorkspaceRepository
from app.services.content_plan_service import ContentPlanService
from app.services.draft_service import DraftService
from app.services.email_service import EmailService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notion_service import NotionService
from app.services.report_service import ReportService
from app.services.social_connection_service import SocialConnectionService
from app.services.social_publishing_service import SocialPublishingService
from app.services.source_analysis_service import SourceAnalysisService
from app.services.source_discovery_service import SourceDiscoveryService
from app.services.workspace_service import (
    DEFAULT_WORKSPACE_ID,
    Membership,
    WorkspaceService,
    can_edit,
    can_manage_integrations,
    can_manage_team,
    can_publish,
    generate_token,
    hash_share_password,
    is_valid_role,
    verify_share_password,
)
from app.utils.errors import (
    AIServiceError,
    BlotatoServiceError,
    GrowlyError,
    IntegrationError,
    WorkspaceAccessError,
)

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


def get_workspace_id(
    x_growly_workspace_id: str | None = Header(default=None),
) -> str:
    return (x_growly_workspace_id or "").strip() or "default"


def get_user_email(
    x_growly_user_email: str | None = Header(default=None),
) -> str | None:
    return (x_growly_user_email or "").strip() or None


def current_membership(
    email: str | None = Depends(get_user_email),
    x_growly_workspace_id: str | None = Header(default=None),
) -> Membership | None:
    """Resolve the caller's workspace membership.

    Returns ``None`` for the legacy/unauthenticated path (no verified email
    forwarded by the proxy), which leaves existing single-tenant behaviour
    untouched. When an email *is* present, an authenticated non-member is
    denied (403) so they can never see another workspace's data.
    """
    if not email:
        return None
    return WorkspaceService().require_membership(email, x_growly_workspace_id)


def effective_workspace_id(
    workspace_id: str = Depends(get_workspace_id),
    membership: Membership | None = Depends(current_membership),
) -> str:
    return membership.workspace_id if membership is not None else workspace_id


def require_member(
    membership: Membership | None = Depends(current_membership),
) -> Membership:
    if membership is None:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=403
        )
    return membership


def _visible_in_workspace(
    resource_workspace_id: str | None, membership: Membership | None
) -> bool:
    """Read-side workspace check: legacy rows (NULL workspace) and the legacy
    no-auth path stay visible; otherwise the row must match the caller's
    workspace.
    """
    if membership is None:
        return True
    if resource_workspace_id is None:
        return membership.workspace_id == DEFAULT_WORKSPACE_ID
    return resource_workspace_id == membership.workspace_id


def _stamp_workspace(model: Any, obj_id: int | None, workspace_id: str | None) -> None:
    """Assign a freshly-created resource to the caller's workspace.

    Only stamps rows that have no workspace yet, so it never moves data between
    workspaces. No-op in the legacy/no-auth path (workspace_id is None).
    """
    if not workspace_id or obj_id is None:
        return
    with session_scope() as session:
        row = session.get(model, obj_id)
        if row is not None and getattr(row, "workspace_id", None) is None:
            row.workspace_id = workspace_id


def require_admin(
    x_growly_user_email: str | None = Header(default=None),
    x_growly_admin_secret: str | None = Header(default=None),
) -> str:
    """Gate admin endpoints. Admins are identified by ADMIN_EMAILS (matched
    against the session email injected by the proxy) or a shared ADMIN_SECRET.
    Public by default is disallowed: with neither configured, access is denied.
    """
    settings = get_settings()
    admin_emails = settings.admin_email_set()
    email = (x_growly_user_email or "").strip().lower()
    if admin_emails and email in admin_emails:
        return email
    secret = settings.admin_secret_value()
    if (
        secret
        and x_growly_admin_secret
        and hmac.compare_digest(secret, x_growly_admin_secret.strip())
    ):
        return email or "admin"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Доступ только для администратора.",
    )


secured_router = APIRouter(dependencies=[Depends(require_web_api_key)])
admin_router = APIRouter(
    prefix="/admin", dependencies=[Depends(require_web_api_key)]
)


class MarketScanRequest(BaseModel):
    niche: str = Field(min_length=2, max_length=300)
    region_language: str = Field(default="Казахстан, русский язык", max_length=300)
    competitor_keywords: str = Field(default="", max_length=500)
    language: Literal["ru", "en", "kk"] = "ru"


class CompetitorReportRequest(BaseModel):
    query: str | None = Field(default=None, max_length=500)
    report_id: int | None = Field(default=None, ge=1)
    language: Literal["ru", "en", "kk"] = "ru"


class ContentPlanRequest(BaseModel):
    weekly_objective: str = Field(default="", max_length=2000)
    business: dict[str, Any] = Field(default_factory=dict)
    report_id: int | None = Field(default=None, ge=1)
    goal: str | None = Field(default=None, max_length=600)
    audience: str | None = Field(default=None, max_length=600)
    offer: str | None = Field(default=None, max_length=600)
    channels: list[str] = Field(default_factory=list, max_length=12)
    content_types: list[str] = Field(default_factory=list, max_length=12)
    cta: str | None = Field(default=None, max_length=600)
    custom_instruction: str | None = Field(default=None, max_length=2000)
    language: Literal["ru", "en", "kk"] = "ru"


class ContentPlanOptionsRequest(BaseModel):
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
        "ideas",
        "ask",
    ] | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    report_id: int | None = Field(default=None, ge=1)
    language: Literal["ru", "en", "kk"] = "ru"


class ActiveContextRequest(BaseModel):
    active_report_id: int | None = Field(default=None, ge=1)


class BlotatoMappingItem(BaseModel):
    platform: str = Field(min_length=1, max_length=50)
    account_id: str | None = Field(default=None, max_length=200)
    page_id: str | None = Field(default=None, max_length=200)


class BlotatoMappingsRequest(BaseModel):
    workspace_id: str | None = Field(default=None, max_length=200)
    mappings: list[BlotatoMappingItem] = Field(default_factory=list, max_length=40)


class SocialConnectionRequestBody(BaseModel):
    platform: Literal["instagram", "threads", "tiktok", "youtube", "facebook", "linkedin", "x"] = "instagram"
    username: str | None = Field(default=None, max_length=120)


class SocialDisconnectRequest(BaseModel):
    platform: str = Field(default="instagram", min_length=1, max_length=50)


class AdminRequestStatusBody(BaseModel):
    status: Literal["pending", "in_progress", "connected", "cancelled", "failed"]
    admin_note: str | None = Field(default=None, max_length=2000)


class AdminLinkAccountBody(BaseModel):
    external_account_id: str = Field(min_length=1, max_length=200)
    request_id: int | None = Field(default=None, ge=1)
    workspace_id: str | None = Field(default=None, max_length=200)


class AdminUnlinkAccountBody(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=200)
    platform: str = Field(default="instagram", min_length=1, max_length=50)


class PublishBlotatoRequest(BaseModel):
    platforms: list[str] = Field(min_length=1, max_length=15)
    publish_now: bool = True
    scheduled_time: str | None = Field(default=None, max_length=60)
    media_urls: list[str] = Field(default_factory=list, max_length=20)
    language: Literal["ru", "en", "kk"] = "ru"


class ScheduleBlotatoRequest(BaseModel):
    platforms: list[str] = Field(min_length=1, max_length=15)
    scheduled_time: str = Field(min_length=4, max_length=60)
    media_urls: list[str] = Field(default_factory=list, max_length=20)
    language: Literal["ru", "en", "kk"] = "ru"


class ManualPackageRequest(BaseModel):
    platforms: list[str] = Field(min_length=1, max_length=15)
    language: Literal["ru", "en", "kk"] = "ru"


class BlotatoMediaUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=240)


class BlotatoVisualRequest(BaseModel):
    kind: Literal["image", "video"]
    prompt: str = Field(min_length=5, max_length=6000)
    title: str | None = Field(default=None, max_length=200)


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


def _content_plan_workspace_filter(workspace_id: str):
    # Legacy rows (NULL workspace) remain visible only in the legacy default
    # workspace. Private workspaces must not see global single-tenant leftovers.
    if workspace_id == DEFAULT_WORKSPACE_ID:
        return or_(
            ContentPlan.workspace_id == workspace_id,
            ContentPlan.workspace_id.is_(None),
        )
    return ContentPlan.workspace_id == workspace_id


def _list_content_plan_response(
    limit: int, workspace_id: str | None = None
) -> dict[str, Any]:
    with session_scope() as session:
        anchor_statement = select(ContentPlan).order_by(
            desc(ContentPlan.created_at), desc(ContentPlan.id)
        )
        if workspace_id is not None:
            anchor_statement = anchor_statement.where(
                _content_plan_workspace_filter(workspace_id)
            )
        anchor = session.scalar(anchor_statement.limit(1))
        if anchor is None:
            return {
                "plan_id": None,
                "content_plan_id": None,
                "items": [],
                "source": _content_plan_source_payload(session),
            }
        rows = _content_plan_batch_rows(
            session, anchor, limit=limit, workspace_id=workspace_id
        )
        plan_id = min(row.id for row in rows)
        return {
            "plan_id": plan_id,
            "content_plan_id": plan_id,
            "items": [_content_plan_payload(row) for row in rows],
            "source": _content_plan_source_payload(session),
        }


def _content_plan_batch_rows(
    session: Any,
    anchor: ContentPlan,
    *,
    limit: int | None = None,
    workspace_id: str | None = None,
) -> list[ContentPlan]:
    if anchor.created_at is None:
        return [anchor]
    statement = select(ContentPlan).where(
        ContentPlan.created_at == anchor.created_at
    )
    if workspace_id is not None:
        statement = statement.where(
            _content_plan_workspace_filter(workspace_id)
        )
    statement = statement.order_by(ContentPlan.publish_date, ContentPlan.id)
    if limit is not None:
        statement = statement.limit(limit)
    rows = list(session.scalars(statement))
    return rows or [anchor]


def _content_plan_detail_response(
    plan_id: int, workspace_id: str | None = None
) -> dict[str, Any]:
    with session_scope() as session:
        anchor = session.get(ContentPlan, plan_id)
        if anchor is None:
            raise HTTPException(status_code=404, detail="Контент-план не найден.")
        if workspace_id is not None:
            visible = (
                anchor.workspace_id == workspace_id
                or (
                    anchor.workspace_id is None
                    and workspace_id == DEFAULT_WORKSPACE_ID
                )
            )
            if not visible:
                raise HTTPException(status_code=404, detail="Контент-план не найден.")
        rows = _content_plan_batch_rows(
            session, anchor, workspace_id=workspace_id
        )
        try:
            draft_ids = DraftsRepository(session).latest_ids_for_plans(
                [row.id for row in rows]
            )
        except Exception:  # noqa: BLE001 - draft links are best-effort
            draft_ids = {}
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = _content_plan_payload(row)
            payload["draft_id"] = draft_ids.get(row.id)
            items.append(payload)
        return {
            "plan_id": min(row.id for row in rows),
            "items": items,
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
async def market_scan(
    payload: MarketScanRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    service = MarketIntelligenceService()
    if membership is not None:
        job = await service.create_market_scan_job(
            None, payload.niche, workspace_id=membership.workspace_id
        )
    else:
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
async def competitor_report(
    payload: CompetitorReportRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    report = await MarketIntelligenceService().generate_competitor_report(
        query=payload.query,
        market_report_id=payload.report_id,
        output_language=payload.language,
    )
    if membership is not None:
        await asyncio.to_thread(
            _stamp_workspace, Report, report.id, membership.workspace_id
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
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    if membership is None:
        return await asyncio.to_thread(_list_content_plan_response, limit)
    return await asyncio.to_thread(
        _list_content_plan_response, limit, membership.workspace_id
    )


@secured_router.get("/content-plans")
async def content_plans_list(
    limit: int = Query(default=40, ge=1, le=200),
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    return await content_plan_list(limit=limit, membership=membership)


@secured_router.get("/content-plans/{plan_id}")
async def content_plan_detail(
    plan_id: int,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    if membership is None:
        return await asyncio.to_thread(_content_plan_detail_response, plan_id)
    return await asyncio.to_thread(
        _content_plan_detail_response, plan_id, membership.workspace_id
    )


def _build_content_plan_context(payload: ContentPlanRequest) -> dict[str, Any]:
    labels = {
        "ru": {
            "goal": "Цель",
            "audience": "Аудитория",
            "offer": "Оффер",
            "cta": "Призыв к действию",
            "channels": "Каналы",
            "formats": "Форматы",
            "default": "Контент-план на основе выбранного отчёта.",
        },
        "en": {
            "goal": "Goal",
            "audience": "Audience",
            "offer": "Offer",
            "cta": "Call to action",
            "channels": "Channels",
            "formats": "Formats",
            "default": "Content plan based on the selected report.",
        },
        "kk": {
            "goal": "Мақсат",
            "audience": "Аудитория",
            "offer": "Оффер",
            "cta": "Әрекетке шақыру",
            "channels": "Арналар",
            "formats": "Форматтар",
            "default": "Таңдалған есеп негізіндегі контент-жоспар.",
        },
    }[payload.language]
    parts: list[str] = []
    if payload.goal:
        parts.append(f"{labels['goal']}: {payload.goal}")
    if payload.audience:
        parts.append(f"{labels['audience']}: {payload.audience}")
    if payload.offer:
        parts.append(f"{labels['offer']}: {payload.offer}")
    if payload.cta:
        parts.append(f"{labels['cta']}: {payload.cta}")
    if payload.channels:
        parts.append(f"{labels['channels']}: {', '.join(payload.channels)}")
    if payload.content_types:
        parts.append(f"{labels['formats']}: {', '.join(payload.content_types)}")
    if payload.custom_instruction and payload.custom_instruction.strip():
        parts.append(payload.custom_instruction.strip())
    objective = payload.weekly_objective.strip() or "; ".join(parts)
    if not objective.strip():
        objective = labels["default"]

    business: dict[str, Any] = {**payload.business, "language": payload.language}
    if payload.audience:
        business.setdefault("target_audience", payload.audience)
    if payload.offer:
        business.setdefault("offer", payload.offer)
    if payload.channels:
        business.setdefault("preferred_channels", payload.channels)

    context: dict[str, Any] = {
        "weekly_objective": objective,
        "business": business,
        "language": payload.language,
    }
    if payload.report_id:
        context["market_context"] = {"report_id": payload.report_id}
    elif isinstance(payload.business.get("market_context"), dict):
        context["market_context"] = payload.business["market_context"]
    return context


@secured_router.post("/content-plan")
async def content_plan_create(
    payload: ContentPlanRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    items = await ContentPlanService().generate_weekly_plan(
        _build_content_plan_context(payload)
    )
    plan_id = items[0].id if items else None
    if membership is not None:
        for item in items:
            await asyncio.to_thread(
                _stamp_workspace, ContentPlan, item.id, membership.workspace_id
            )
    return {
        "status": "completed",
        "plan_id": plan_id,
        "content_plan_id": plan_id,
        "items": [_content_plan_payload(item) for item in items],
    }


@secured_router.post("/content-plans")
async def content_plans_create(
    payload: ContentPlanRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    return await content_plan_create(payload, membership=membership)


@secured_router.post("/content-plan/{item_id}/draft")
async def content_plan_draft(
    item_id: int,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    draft = await DraftService().create_from_plan(item_id)
    if membership is not None:
        await asyncio.to_thread(
            _stamp_workspace, Draft, draft.id, membership.workspace_id
        )
    return {
        "status": "completed",
        "draft_id": draft.id,
        "draft": _draft_payload(draft),
    }


@secured_router.post("/create-post")
async def create_post(
    payload: CreatePostRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    draft = await DraftService().create_post(payload.model_dump(exclude_none=True))
    if membership is not None:
        await asyncio.to_thread(
            _stamp_workspace, Draft, draft.id, membership.workspace_id
        )
    return {
        "status": "completed",
        "draft_id": draft.id,
        "draft": _draft_payload(draft),
    }


@secured_router.get("/drafts")
async def drafts(
    limit: int = Query(default=50, ge=1, le=200),
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    def load() -> list[Draft]:
        with session_scope() as session:
            return DraftsRepository(session).list_recent(limit)

    rows = await asyncio.to_thread(load)
    rows = [
        row
        for row in rows
        if _visible_in_workspace(getattr(row, "workspace_id", None), membership)
    ]
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
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    rows = await ReportService().list_latest(limit)
    rows = [
        row
        for row in rows
        if _visible_in_workspace(getattr(row, "workspace_id", None), membership)
    ]
    return {"items": [_report_payload(row) for row in rows]}


@secured_router.get("/reports/{report_id}")
async def report(
    report_id: int,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    row = await ReportService().get_report(report_id)
    if row is None or not _visible_in_workspace(
        getattr(row, "workspace_id", None), membership
    ):
        raise HTTPException(status_code=404, detail="Отчёт не найден.")
    return {"report": _report_payload(row)}


@secured_router.post("/reports/{report_id}/content-plan-options")
async def report_content_plan_options(
    report_id: int,
    payload: ContentPlanOptionsRequest,
) -> dict[str, Any]:
    try:
        options = await ContentPlanService().generate_content_plan_options(
            report_id,
            payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return options


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


def _action_error_status(exc: Exception) -> int:
    if isinstance(exc, AIServiceError):
        status_code = exc.status
        if isinstance(status_code, int) and 400 <= status_code < 600:
            return status_code
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if isinstance(exc, TimeoutError):
        return status.HTTP_504_GATEWAY_TIMEOUT
    if isinstance(exc, IntegrationError):
        status_code = getattr(exc, "status", None)
        if isinstance(status_code, int) and 400 <= status_code < 600:
            return status_code
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_400_BAD_REQUEST


def _action_error_detail(exc: Exception) -> str:
    if isinstance(exc, AIServiceError):
        if exc.is_rate_limited:
            return (
                "Генерация временно недоступна: лимит AI-сервиса исчерпан. "
                "Попробуйте позже."
            )
        return "Генерация временно недоступна. Попробуйте позже."
    if isinstance(exc, TimeoutError):
        return "Генерация заняла слишком много времени. Попробуйте ещё раз."
    message = str(exc).strip()
    return message or "Задачу не удалось выполнить. Сервис временно недоступен."


def _raise_action_error(exc: Exception) -> NoReturn:
    raise HTTPException(
        status_code=_action_error_status(exc),
        detail=_action_error_detail(exc),
    ) from exc


@secured_router.post("/chat")
async def chat(
    payload: ChatRequest,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    context = payload.context
    report_id = payload.report_id
    if report_id is None and str(context.get("report_id") or "").isdigit():
        report_id = int(context["report_id"])
    action = payload.action or _infer_chat_action(payload.message)
    if action is None and report_id is not None:
        action = "ask"
    if action == "ask":
        if report_id is None:
            raise HTTPException(status_code=400, detail="Сначала выберите отчёт.")
        try:
            answer = await ReportService().answer_question(
                report_id,
                payload.message,
                payload.language,
            )
        except (GrowlyError, TimeoutError) as exc:
            _raise_action_error(exc)
        return {
            "status": "completed",
            "action": "ask",
            "message": "Готово.",
            "result": {"answer": answer},
        }
    if action == "ideas":
        if report_id is None:
            raise HTTPException(status_code=400, detail="Сначала выберите отчёт.")
        try:
            answer = await ReportService().report_ideas(report_id, payload.language)
        except (GrowlyError, TimeoutError) as exc:
            _raise_action_error(exc)
        return {
            "status": "completed",
            "action": "ideas",
            "message": "Готово.",
            "result": {"answer": answer},
        }
    try:
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
                    report_id=report_id,
                    language=payload.language,
                ),
                membership=membership,
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
                    report_id=report_id,
                    language=payload.language,
                ),
                membership=membership,
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
                ),
                membership=membership,
            )
        elif action == "drafts":
            result = await drafts(limit=50, membership=membership)
        elif action == "reports":
            result = await reports(limit=50, membership=membership)
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
    except (GrowlyError, TimeoutError) as exc:
        _raise_action_error(exc)
    return {
        "status": "completed",
        "action": action,
        "message": "Задача выполнена.",
        "result": result,
    }


@secured_router.get("/integrations/status")
async def integrations_status(
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return await SocialPublishingService().integrations_status(workspace_id)


@secured_router.get("/integrations/blotato/status")
async def blotato_status(
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return await SocialPublishingService().blotato_status(workspace_id)


@secured_router.get("/integrations/blotato/accounts")
async def blotato_accounts(
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    accounts = await SocialPublishingService().list_accounts(workspace_id)
    return {"accounts": accounts}


def _safe_blotato_detail(exc: BlotatoServiceError) -> str:
    provider_message = (exc.provider_message or "").strip()
    if provider_message and provider_message != str(exc):
        return f"{exc} Blotato: {provider_message}"
    return str(exc)


@secured_router.post("/integrations/blotato/media-upload")
async def blotato_media_upload(
    payload: BlotatoMediaUploadRequest,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, str]:
    try:
        return await SocialPublishingService().create_media_upload(
            workspace_id, payload.filename
        )
    except BlotatoServiceError as exc:
        raise HTTPException(
            status_code=502, detail=_safe_blotato_detail(exc)
        ) from exc


@secured_router.post("/integrations/blotato/visuals")
async def blotato_create_visual(
    payload: BlotatoVisualRequest,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    try:
        return await SocialPublishingService().create_visual(
            workspace_id,
            kind=payload.kind,
            prompt=payload.prompt,
            title=payload.title,
        )
    except BlotatoServiceError as exc:
        raise HTTPException(
            status_code=502, detail=_safe_blotato_detail(exc)
        ) from exc


@secured_router.get("/integrations/blotato/visuals/{visual_id}")
async def blotato_visual_status(
    visual_id: str,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    if not visual_id.strip() or len(visual_id) > 200:
        raise HTTPException(status_code=400, detail="Некорректный ID медиа.")
    try:
        return await SocialPublishingService().visual_status(
            workspace_id, visual_id
        )
    except BlotatoServiceError as exc:
        raise HTTPException(
            status_code=502, detail=_safe_blotato_detail(exc)
        ) from exc


# -- user-facing social connection (admin-assisted manual MVP) ------------


@secured_router.get("/integrations/social/status")
async def social_status(
    platform: str = Query(default="instagram", max_length=50),
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return await SocialConnectionService().status(workspace_id, platform)


@secured_router.post("/integrations/social/request")
async def social_request(
    payload: SocialConnectionRequestBody,
    workspace_id: str = Depends(effective_workspace_id),
    user_email: str | None = Depends(get_user_email),
) -> dict[str, Any]:
    try:
        return await SocialConnectionService().create_request(
            workspace_id, user_email, payload.platform, payload.username
        )
    except GrowlyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@secured_router.delete("/integrations/social/request/{request_id}")
async def social_cancel_request(
    request_id: int,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    try:
        return await SocialConnectionService().cancel_request(
            workspace_id, request_id
        )
    except GrowlyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@secured_router.post("/integrations/social/disconnect")
async def social_disconnect(
    payload: SocialDisconnectRequest,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return await SocialConnectionService().disconnect(
        workspace_id, payload.platform
    )


@secured_router.post("/integrations/blotato/test")
async def blotato_test(
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return await SocialPublishingService().test_connection(workspace_id)


@secured_router.post("/integrations/blotato/mappings")
async def blotato_set_mappings(
    payload: BlotatoMappingsRequest,
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    target_workspace = payload.workspace_id or workspace_id
    saved = await SocialPublishingService().save_mappings(
        target_workspace,
        [item.model_dump() for item in payload.mappings],
    )
    return {"mappings": saved}


@secured_router.get("/integrations/blotato/mappings")
async def blotato_get_mappings(
    workspace_id: str = Depends(effective_workspace_id),
) -> dict[str, Any]:
    return {
        "mappings": await SocialPublishingService().get_mappings(workspace_id)
    }


@secured_router.get("/drafts/{draft_id}")
async def draft_detail(
    draft_id: int,
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    def load() -> Draft | None:
        with session_scope() as session:
            return DraftsRepository(session).get(draft_id)

    row = await asyncio.to_thread(load)
    if row is None or not _visible_in_workspace(
        getattr(row, "workspace_id", None), membership
    ):
        raise HTTPException(status_code=404, detail="Черновик не найден.")
    return {"draft": _draft_payload(row)}


@secured_router.post("/drafts/{draft_id}/publish-blotato")
async def publish_draft_blotato(
    draft_id: int,
    payload: PublishBlotatoRequest,
    workspace_id: str = Depends(effective_workspace_id),
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    if membership is not None and not can_publish(membership.role):
        raise WorkspaceAccessError(
            "У вашей роли нет прав на публикацию.", status=403
        )
    try:
        return await SocialPublishingService().publish_draft(
            workspace_id=workspace_id,
            draft_id=draft_id,
            platforms=payload.platforms,
            publish_now=payload.publish_now,
            scheduled_time=payload.scheduled_time,
            media_urls=payload.media_urls,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@secured_router.post("/drafts/{draft_id}/schedule-blotato")
async def schedule_draft_blotato(
    draft_id: int,
    payload: ScheduleBlotatoRequest,
    workspace_id: str = Depends(effective_workspace_id),
    membership: Membership | None = Depends(current_membership),
) -> dict[str, Any]:
    if membership is not None and not can_publish(membership.role):
        raise WorkspaceAccessError(
            "У вашей роли нет прав на публикацию.", status=403
        )
    try:
        return await SocialPublishingService().publish_draft(
            workspace_id=workspace_id,
            draft_id=draft_id,
            platforms=payload.platforms,
            publish_now=False,
            scheduled_time=payload.scheduled_time,
            media_urls=payload.media_urls,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@secured_router.post("/drafts/{draft_id}/manual-package")
async def draft_manual_package(
    draft_id: int,
    payload: ManualPackageRequest,
    workspace_id: str = Depends(get_workspace_id),
) -> dict[str, Any]:
    try:
        packages = await SocialPublishingService().create_manual_package(
            workspace_id=workspace_id,
            draft_id=draft_id,
            platforms=payload.platforms,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"packages": packages}


@secured_router.post("/content-items/{item_id}/create-manual-package")
async def content_item_manual_package(
    item_id: int,
    payload: ManualPackageRequest,
    workspace_id: str = Depends(get_workspace_id),
) -> dict[str, Any]:
    return await draft_manual_package(item_id, payload, workspace_id)


@secured_router.get("/publications/{publication_id}/status")
async def publication_status(publication_id: int) -> dict[str, Any]:
    try:
        return await SocialPublishingService().publication_status(publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# -- admin: Blotato + social connection management ------------------------


@admin_router.get("/blotato/status")
async def admin_blotato_status(
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    return await SocialConnectionService().admin_blotato_status()


@admin_router.get("/blotato/accounts")
async def admin_blotato_accounts(
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        accounts = await SocialConnectionService().admin_list_accounts()
    except BlotatoServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"accounts": accounts}


@admin_router.get("/social-connection-requests")
async def admin_list_requests(
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    requests = await SocialConnectionService().admin_list_requests(status_filter)
    return {"requests": requests}


@admin_router.post("/social-connection-requests/{request_id}/status")
async def admin_set_request_status(
    request_id: int,
    payload: AdminRequestStatusBody,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return await SocialConnectionService().admin_set_request_status(
            request_id, payload.status, payload.admin_note
        )
    except GrowlyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/social-accounts/link")
async def admin_link_account(
    payload: AdminLinkAccountBody,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        account = await SocialConnectionService().admin_link_account(
            external_account_id=payload.external_account_id,
            request_id=payload.request_id,
            workspace_id=payload.workspace_id,
        )
    except BlotatoServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GrowlyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "account": account}


@admin_router.post("/social-accounts/unlink")
async def admin_unlink_account(
    payload: AdminUnlinkAccountBody,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    return await SocialConnectionService().admin_unlink_account(
        payload.workspace_id, payload.platform
    )


# ==========================================================================
# Workspace / team access, invitations, share links and tasks
# ==========================================================================

INVITE_TTL_DAYS = 14
_INVITE_ROLES = {"viewer", "editor", "admin"}


class InvitationCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["viewer", "editor", "admin"] = "viewer"
    message: str | None = Field(default=None, max_length=2000)


class MemberRoleUpdateRequest(BaseModel):
    role: Literal["owner", "admin", "editor", "viewer"]


class ShareLinkCreateRequest(BaseModel):
    resource_type: Literal["workspace", "report", "content_plan", "draft"]
    resource_id: int | None = Field(default=None, ge=1)
    password: str | None = Field(default=None, min_length=1, max_length=200)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    source_type: Literal["report", "content_plan", "draft", "manual"] = "manual"
    source_id: int | None = Field(default=None, ge=1)
    assignee_email: str | None = Field(default=None, max_length=320)
    status: Literal["todo", "in_progress", "done", "cancelled"] = "todo"
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: date | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    assignee_email: str | None = Field(default=None, max_length=320)
    status: Literal["todo", "in_progress", "done", "cancelled"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: date | None = None


def _member_payload(member: Any) -> dict[str, Any]:
    return {
        "id": member.id,
        "workspace_id": member.workspace_id,
        "email": member.email,
        "role": member.role,
        "status": member.status,
        "invited_by": member.invited_by,
        "invited_at": _date_value(member.invited_at),
        "joined_at": _date_value(member.joined_at),
        "created_at": _date_value(member.created_at),
        "updated_at": _date_value(member.updated_at),
    }


def _invitation_payload(inv: Any) -> dict[str, Any]:
    return {
        "id": inv.id,
        "workspace_id": inv.workspace_id,
        "email": inv.email,
        "role": inv.role,
        "token": inv.token,
        "status": inv.status,
        "invited_by": inv.invited_by,
        "expires_at": _date_value(inv.expires_at),
        "accepted_at": _date_value(inv.accepted_at),
        "created_at": _date_value(inv.created_at),
        "invite_path": f"/invite/{inv.token}",
    }


def _task_payload(task: Any) -> dict[str, Any]:
    return {
        "id": task.id,
        "workspace_id": task.workspace_id,
        "source_type": task.source_type,
        "source_id": task.source_id,
        "title": task.title,
        "description": task.description,
        "assignee_email": task.assignee_email,
        "status": task.status,
        "priority": task.priority,
        "due_date": _date_value(task.due_date),
        "created_by": task.created_by,
        "created_at": _date_value(task.created_at),
        "updated_at": _date_value(task.updated_at),
    }


def _share_link_payload(link: Any) -> dict[str, Any]:
    return {
        "id": link.id,
        "token": link.token,
        "resource_type": link.resource_type,
        "resource_id": link.resource_id,
        "access_level": link.access_level,
        "has_password": bool(link.password_hash),
        "expires_at": _date_value(link.expires_at),
        "is_active": link.is_active,
        "created_at": _date_value(link.created_at),
        "share_path": f"/share/{link.resource_type}/{link.token}",
    }


@secured_router.get("/workspaces/current")
async def workspace_current(
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    return {
        "workspace_id": membership.workspace_id,
        "email": membership.email,
        "role": membership.role,
        "permissions": {
            "can_view": True,
            "can_edit": can_edit(membership.role),
            "can_publish": can_publish(membership.role),
            "can_manage_team": can_manage_team(membership.role),
            "can_manage_integrations": can_manage_integrations(membership.role),
        },
    }


@secured_router.get("/workspaces/{workspace_id}/members")
async def workspace_members(
    workspace_id: str,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    if membership.workspace_id != workspace_id:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=404
        )

    def load() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            members = repo.list_members(workspace_id)
            invitations = repo.list_invitations(workspace_id, status="pending")
            return {
                "members": [_member_payload(m) for m in members],
                "invitations": [_invitation_payload(i) for i in invitations],
            }

    return await asyncio.to_thread(load)


@secured_router.post("/workspaces/{workspace_id}/invitations")
async def create_invitation(
    workspace_id: str,
    payload: InvitationCreateRequest,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    if membership.workspace_id != workspace_id:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=404
        )
    WorkspaceService.require_can_manage_team(membership)
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Укажите корректный email.")
    token = generate_token()
    expires_at = datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS)

    def create() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            existing = repo.get_member_in_workspace(workspace_id, email)
            if existing is not None and existing.status == "active":
                raise WorkspaceAccessError(
                    "Этот участник уже в команде.", status=409
                )
            invitation = repo.create_invitation(
                workspace_id=workspace_id,
                email=email,
                role=payload.role,
                token=token,
                invited_by=membership.email,
                expires_at=expires_at,
            )
            return _invitation_payload(invitation)

    invitation = await asyncio.to_thread(create)
    # Best-effort email delivery; falls back to the copyable link when SMTP is
    # not configured (or sending fails).
    email_sent = False
    email_service = EmailService()
    invite_url = email_service.invite_url(invitation["invite_path"])
    if invite_url:
        role_labels = {
            "viewer": "Только просмотр",
            "editor": "Редактор",
            "admin": "Администратор",
            "owner": "Владелец",
        }
        email_sent = await asyncio.to_thread(
            email_service.send_invitation,
            to_email=invitation["email"],
            invite_url=invite_url,
            role_label=role_labels.get(invitation["role"], invitation["role"]),
        )
    return {"status": "created", "invitation": invitation, "email_sent": email_sent}


@secured_router.get("/invitations/{token}")
async def invitation_details(token: str) -> dict[str, Any]:
    def load() -> dict[str, Any]:
        with session_scope() as session:
            invitation = WorkspaceRepository(session).get_invitation_by_token(
                token
            )
            if invitation is None:
                raise HTTPException(
                    status_code=404, detail="Приглашение не найдено."
                )
            expired = (
                invitation.expires_at is not None
                and invitation.expires_at < datetime.now(UTC)
            )
            return {
                "workspace_id": invitation.workspace_id,
                "email": invitation.email,
                "role": invitation.role,
                "status": "expired" if expired else invitation.status,
            }

    return await asyncio.to_thread(load)


@secured_router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    email: str | None = Depends(get_user_email),
) -> dict[str, Any]:
    if not email:
        raise WorkspaceAccessError(
            "Войдите, чтобы принять приглашение.", status=401
        )
    normalized = email.strip().lower()

    def accept() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            invitation = repo.get_invitation_by_token(token)
            if invitation is None:
                raise HTTPException(
                    status_code=404, detail="Приглашение не найдено."
                )
            if invitation.status == "revoked":
                raise WorkspaceAccessError(
                    "Приглашение больше недействительно.", status=410
                )
            if (
                invitation.expires_at is not None
                and invitation.expires_at < datetime.now(UTC)
            ):
                repo.set_invitation_status(invitation, "expired")
                raise WorkspaceAccessError(
                    "Приглашение истекло. Попросите владельца отправить новое.",
                    status=410,
                )
            if invitation.email.strip().lower() != normalized:
                raise WorkspaceAccessError(
                    "Это приглашение отправлено на другой email.", status=403
                )
            existing = repo.get_member_in_workspace(
                invitation.workspace_id, normalized
            )
            if existing is None:
                repo.add_member(
                    workspace_id=invitation.workspace_id,
                    email=normalized,
                    role=invitation.role,
                    status="active",
                    invited_by=invitation.invited_by,
                )
            elif existing.status != "active":
                existing.status = "active"
                existing.role = invitation.role
            repo.set_invitation_status(
                invitation, "accepted", accepted_at=datetime.now(UTC)
            )
            return {"workspace_id": invitation.workspace_id}

    result = await asyncio.to_thread(accept)
    return {"status": "accepted", **result}


@secured_router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}")
async def revoke_invitation(
    workspace_id: str,
    invitation_id: int,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    if membership.workspace_id != workspace_id:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=404
        )
    WorkspaceService.require_can_manage_team(membership)

    def revoke() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            invitation = repo.get_invitation(invitation_id)
            if invitation is None or invitation.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=404, detail="Приглашение не найдено."
                )
            repo.set_invitation_status(invitation, "revoked")
            return {"id": invitation.id, "status": invitation.status}

    result = await asyncio.to_thread(revoke)
    return {"status": "revoked", "invitation": result}


@secured_router.patch("/workspaces/{workspace_id}/members/{member_id}/role")
async def update_member_role(
    workspace_id: str,
    member_id: int,
    payload: MemberRoleUpdateRequest,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    if membership.workspace_id != workspace_id:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=404
        )
    WorkspaceService.require_can_manage_team(membership)
    if not is_valid_role(payload.role):
        raise HTTPException(status_code=400, detail="Недопустимая роль.")

    def update() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            member = repo.get_member(member_id)
            if member is None or member.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=404, detail="Участник не найден."
                )
            # Never leave a workspace without an owner.
            if (
                member.role == "owner"
                and payload.role != "owner"
                and repo.count_owners(workspace_id) <= 1
            ):
                raise WorkspaceAccessError(
                    "Нельзя понизить последнего владельца.", status=409
                )
            repo.update_member_role(member, payload.role)
            return _member_payload(member)

    member = await asyncio.to_thread(update)
    return {"status": "updated", "member": member}


@secured_router.delete("/workspaces/{workspace_id}/members/{member_id}")
async def remove_member(
    workspace_id: str,
    member_id: int,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    if membership.workspace_id != workspace_id:
        raise WorkspaceAccessError(
            "У вас нет доступа к этому workspace.", status=404
        )
    WorkspaceService.require_can_manage_team(membership)

    def remove() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            member = repo.get_member(member_id)
            if member is None or member.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=404, detail="Участник не найден."
                )
            if (
                member.role == "owner"
                and repo.count_owners(workspace_id) <= 1
            ):
                raise WorkspaceAccessError(
                    "Нельзя удалить последнего владельца.", status=409
                )
            repo.remove_member(member)
            return {"id": member.id, "status": member.status}

    result = await asyncio.to_thread(remove)
    return {"status": "removed", "member": result}


@secured_router.post("/share-links")
async def create_share_link(
    payload: ShareLinkCreateRequest,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    WorkspaceService.require_can_manage_team(membership)
    token = generate_token()
    password_hash = (
        hash_share_password(payload.password) if payload.password else None
    )
    expires_at = (
        datetime.now(UTC) + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days
        else None
    )

    def create() -> dict[str, Any]:
        with session_scope() as session:
            link = WorkspaceRepository(session).create_share_link(
                workspace_id=membership.workspace_id,
                resource_type=payload.resource_type,
                resource_id=payload.resource_id,
                token=token,
                password_hash=password_hash,
                expires_at=expires_at,
                created_by=membership.email,
            )
            return _share_link_payload(link)

    link = await asyncio.to_thread(create)
    return {"status": "created", "share_link": link}


@secured_router.delete("/share-links/{link_id}")
async def delete_share_link(
    link_id: int,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    WorkspaceService.require_can_manage_team(membership)

    def deactivate() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            link = repo.get_share_link(link_id)
            if link is None or link.workspace_id != membership.workspace_id:
                raise HTTPException(status_code=404, detail="Ссылка не найдена.")
            repo.deactivate_share_link(link)
            return {"id": link.id, "is_active": link.is_active}

    result = await asyncio.to_thread(deactivate)
    return {"status": "deleted", "share_link": result}


@secured_router.get("/share-links/{token}")
async def resolve_share_link(
    token: str,
    password: str | None = Query(default=None),
) -> dict[str, Any]:
    """Public, view-only resolution of a share link. Requires no membership and
    never exposes integrations, admin notes or publishing controls.
    """

    def resolve() -> dict[str, Any]:
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            link = repo.get_share_link_by_token(token)
            if link is None or not link.is_active:
                raise HTTPException(status_code=404, detail="Ссылка недоступна.")
            if (
                link.expires_at is not None
                and link.expires_at < datetime.now(UTC)
            ):
                raise WorkspaceAccessError(
                    "Срок действия ссылки истёк.", status=410
                )
            if link.password_hash and not verify_share_password(
                password or "", link.password_hash
            ):
                raise WorkspaceAccessError(
                    "Неверный пароль.", status=401
                )
            resource = _load_shared_resource(session, link)
            return {
                "resource_type": link.resource_type,
                "access_level": link.access_level,
                "resource": resource,
            }

    return await asyncio.to_thread(resolve)


def _load_shared_resource(session: Any, link: Any) -> dict[str, Any] | None:
    """Build a sanitized, view-only payload for a shared resource."""
    if link.resource_type == "report" and link.resource_id is not None:
        report = ReportsRepository(session).get_report(link.resource_id)
        if report is None or (
            report.workspace_id is not None
            and report.workspace_id != link.workspace_id
        ):
            return None
        return {
            "title": report.title,
            "summary": report.summary,
            "body": report.body or report.report_text,
            "created_at": _date_value(report.created_at),
        }
    if link.resource_type == "draft" and link.resource_id is not None:
        draft = DraftsRepository(session).get(link.resource_id)
        if draft is None or (
            draft.workspace_id is not None
            and draft.workspace_id != link.workspace_id
        ):
            return None
        return {
            "title": draft.title,
            "text": draft.draft_text,
            "channel": draft.channel,
            "status": draft.status,
            "created_at": _date_value(draft.created_at),
        }
    if link.resource_type == "content_plan" and link.resource_id is not None:
        item = session.get(ContentPlan, link.resource_id)
        if item is None or (
            item.workspace_id is not None
            and item.workspace_id != link.workspace_id
        ):
            return None
        return {
            "topic": item.topic,
            "channel": item.channel,
            "content_type": item.content_type,
            "goal": item.goal,
            "cta": item.cta,
            "status": item.status,
            "publish_date": _date_value(item.publish_date),
        }
    return {"workspace_id": link.workspace_id}


@secured_router.get("/tasks")
async def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    def load() -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = TasksRepository(session).list_for_workspace(
                membership.workspace_id, status=status_filter, limit=limit
            )
            return [_task_payload(row) for row in rows]

    items = await asyncio.to_thread(load)
    return {"items": items}


@secured_router.post("/tasks")
async def create_task(
    payload: TaskCreateRequest,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    WorkspaceService.require_can_edit(membership)

    def create() -> dict[str, Any]:
        with session_scope() as session:
            task = TasksRepository(session).create(
                workspace_id=membership.workspace_id,
                title=payload.title,
                description=payload.description,
                source_type=payload.source_type,
                source_id=payload.source_id,
                assignee_email=payload.assignee_email,
                status=payload.status,
                priority=payload.priority,
                due_date=payload.due_date,
                created_by=membership.email,
            )
            return _task_payload(task)

    task = await asyncio.to_thread(create)
    return {"status": "created", "task": task}


@secured_router.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    WorkspaceService.require_can_edit(membership)

    def update() -> dict[str, Any]:
        with session_scope() as session:
            repo = TasksRepository(session)
            task = repo.get(task_id)
            if task is None or task.workspace_id != membership.workspace_id:
                raise HTTPException(status_code=404, detail="Задача не найдена.")
            repo.update(task, **payload.model_dump(exclude_none=True))
            return _task_payload(task)

    task = await asyncio.to_thread(update)
    return {"status": "updated", "task": task}


@secured_router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    membership: Membership = Depends(require_member),
) -> dict[str, Any]:
    WorkspaceService.require_can_edit(membership)

    def delete() -> dict[str, Any]:
        with session_scope() as session:
            repo = TasksRepository(session)
            task = repo.get(task_id)
            if task is None or task.workspace_id != membership.workspace_id:
                raise HTTPException(status_code=404, detail="Задача не найдена.")
            repo.delete(task)
            return {"id": task_id}

    result = await asyncio.to_thread(delete)
    return {"status": "deleted", "task": result}


router.include_router(secured_router)
router.include_router(admin_router)
