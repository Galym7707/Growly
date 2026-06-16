from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import desc, func, select

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import (
    ContentPlan,
    Draft,
    Publication,
    Report,
    ReviewImport,
    Source,
    SourceItem,
)
from app.repositories.logs_repo import LogsRepository
from app.repositories.settings_repo import SettingsRepository
from app.utils.errors import NotionServiceError

logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2026-03-11"
NOTION_API_BASE = "https://api.notion.com/v1"


def _text(value: str | None, *, limit: int = 1800) -> list[dict[str, Any]]:
    content = (value or "").strip()
    if not content:
        return []
    return [
        {"type": "text", "text": {"content": content[index : index + limit]}}
        for index in range(0, min(len(content), limit * 50), limit)
    ]


def _title(value: str | None) -> dict[str, Any]:
    return {"title": _text(value or "Untitled")}


def _rich_text(value: str | None) -> dict[str, Any]:
    return {"rich_text": _text(value)}


def _select(value: str | None) -> dict[str, Any]:
    return {"select": {"name": value[:100]} if value else None}


def _status_label(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("_", " ").title()


def _number(value: int | float | None) -> dict[str, Any]:
    return {"number": value}


def _date(value: Any) -> dict[str, Any]:
    if value is None:
        return {"date": None}
    iso_value = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return {"date": {"start": iso_value}}


def _url(value: str | None) -> dict[str, Any]:
    return {"url": value or None}


def _paragraphs(value: str | None) -> list[dict[str, Any]]:
    content = (value or "").strip()
    if not content:
        return []
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": _text(content[index : index + 1800])},
        }
        for index in range(0, min(len(content), 1800 * 90), 1800)
    ]


class NotionService:
    database_specs: dict[str, dict[str, Any]] = {
        "Sources": {
            "Name": {"title": {}},
            "Type": {"select": {}},
            "URL": {"url": {}},
            "Category": {"select": {}},
            "Priority": {"select": {}},
            "Status": {"select": {}},
            "Frequency": {"select": {}},
            "Last Checked": {"date": {}},
            "Responsible": {"rich_text": {}},
            "Notes": {"rich_text": {}},
            "Supabase ID": {"number": {}},
        },
        "Source Items": {
            "Title": {"title": {}},
            "URL": {"url": {}},
            "Provider": {"select": {}},
            "Query": {"rich_text": {}},
            "Source Type": {"select": {}},
            "Snippet": {"rich_text": {}},
            "AI Summary": {"rich_text": {}},
            "Topics": {"rich_text": {}},
            "Offers": {"rich_text": {}},
            "CTAs": {"rich_text": {}},
            "Pains": {"rich_text": {}},
            "Content Gaps": {"rich_text": {}},
            "Status": {"select": {}},
            "Created At": {"date": {}},
            "Source": {"rich_text": {}},
            "Source ID": {"number": {}},
            "Topic": {"rich_text": {}},
            "Format": {"select": {}},
            "Offer": {"rich_text": {}},
            "CTA": {"rich_text": {}},
            "Pain": {"rich_text": {}},
            "Hook": {"rich_text": {}},
            "Summary": {"rich_text": {}},
            "Risk": {"rich_text": {}},
            "Adaptation Idea": {"rich_text": {}},
            "Supabase ID": {"number": {}},
        },
        "Content Calendar": {
            "Topic": {"title": {}},
            "Publish Date": {"date": {}},
            "Channel": {"select": {}},
            "Content Type": {"select": {}},
            "Goal": {"rich_text": {}},
            "Target Audience": {"rich_text": {}},
            "CTA": {"rich_text": {}},
            "Source Idea": {"rich_text": {}},
            "Why Recommended": {"rich_text": {}},
            "Status": {"select": {}},
            "Supabase ID": {"number": {}},
        },
        "Drafts": {
            "Title": {"title": {}},
            "Status": {"select": {}},
            "Version": {"number": {}},
            "Channel": {"select": {}},
            "Type": {"select": {}},
            "Draft Text": {"rich_text": {}},
            "Prompt": {"rich_text": {}},
            "AI Model": {"rich_text": {}},
            "Content Plan ID": {"number": {}},
            "Supabase ID": {"number": {}},
        },
        "Reports": {
            "Title": {"title": {}},
            "Report Type": {"select": {}},
            "Query": {"rich_text": {}},
            "Sources Count": {"number": {}},
            "Created At": {"date": {}},
            "Type": {"select": {}},
            "Week Start": {"date": {}},
            "Week End": {"date": {}},
            "Status": {"select": {}},
            "Report Text": {"rich_text": {}},
            "Summary": {"rich_text": {}},
            "Recommendations": {"rich_text": {}},
            "Supabase ID": {"number": {}},
        },
        "Reviews and Market Insights": {
            "Title": {"title": {}},
            "Source": {"rich_text": {}},
            "Summary": {"rich_text": {}},
            "Pains": {"rich_text": {}},
            "Objections": {"rich_text": {}},
            "Content Ideas": {"rich_text": {}},
            "Supabase ID": {"number": {}},
        },
        "Publications": {
            "Title": {"title": {}},
            "Channel": {"select": {}},
            "Status": {"select": {}},
            "Published URL": {"url": {}},
            "Published At": {"date": {}},
            "Views": {"number": {}},
            "Reactions": {"number": {}},
            "Comments": {"number": {}},
            "Clicks": {"number": {}},
            "Leads": {"number": {}},
            "Telegram Message ID": {"rich_text": {}},
            "Notes": {"rich_text": {}},
            "Supabase ID": {"number": {}},
        },
        "Integration Status": {
            "Integration": {"title": {}},
            "Status": {"select": {}},
            "Details": {"rich_text": {}},
            "Last Checked": {"date": {}},
        },
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.notion_token()}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    async def _record_failure(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        def write_log() -> None:
            try:
                with session_scope() as session:
                    LogsRepository(session).create(
                        level="ERROR",
                        module="notion",
                        message=message,
                        details=details,
                    )
            except Exception:
                logger.exception("Could not persist Notion integration error.")

        await asyncio.to_thread(write_log)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_status: int | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.request(
                        method,
                        f"{NOTION_API_BASE}{path}",
                        headers=self.headers,
                        json=json,
                    )
                last_status = response.status_code
                if response.status_code == 429 or response.status_code >= 500:
                    delay = float(response.headers.get("Retry-After", 2**attempt))
                    await asyncio.sleep(min(delay, 10))
                    continue
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    break
                await asyncio.sleep(2**attempt)
            except httpx.HTTPStatusError as exc:
                try:
                    error_payload = exc.response.json()
                except ValueError:
                    error_payload = {}
                notion_code = str(error_payload.get("code") or "unknown_error")
                notion_message = str(
                    error_payload.get("message")
                    or exc.response.reason_phrase
                    or "Notion request failed."
                )
                await self._record_failure(
                    "Notion request was rejected.",
                    {
                        "status_code": exc.response.status_code,
                        "code": notion_code,
                        "notion_message": notion_message,
                        "method": method,
                        "path": path,
                    },
                )
                raise NotionServiceError(
                    f"Notion request failed with status {exc.response.status_code}.",
                    status=exc.response.status_code,
                    code=notion_code,
                    notion_message=notion_message,
                ) from exc
        await self._record_failure(
            "Notion request failed after retries.",
            {"status_code": last_status, "method": method, "path": path},
        )
        raise NotionServiceError(
            "Notion is temporarily unavailable.",
            status=last_status,
            code="temporarily_unavailable",
            notion_message="Notion request failed after retries.",
        )

    async def check_access(self) -> dict[str, Any]:
        root_id = self.settings.require_text(
            "notion_root_page_id", "NOTION_ROOT_PAGE_ID"
        )
        return await self._request("GET", f"/pages/{root_id}")

    async def check_connection(self) -> dict[str, Any]:
        return await self._request("GET", "/users/me")

    async def retrieve_page(self, object_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/pages/{object_id}")

    async def retrieve_database(self, object_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/databases/{object_id}")

    async def search_accessible_objects(
        self, query: str | None = None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if query:
                payload["query"] = query
            if cursor:
                payload["start_cursor"] = cursor
            response = await self._request("POST", "/search", json=payload)
            results.extend(
                row
                for row in response.get("results", [])
                if row.get("object") in {"page", "database", "data_source"}
            )
            if not response.get("has_more"):
                return results
            cursor = response.get("next_cursor")

    async def _get_setting(self, key: str) -> str | None:
        def read() -> str | None:
            with session_scope() as session:
                return SettingsRepository(session).get(key)

        return await asyncio.to_thread(read)

    async def _set_settings(
        self, values: dict[str, str], workspace_id: str | None = None
    ) -> None:
        def write() -> None:
            with session_scope() as session:
                repo = SettingsRepository(session)
                for key, value in values.items():
                    repo.set(key, value, workspace_id=workspace_id)

        await asyncio.to_thread(write)

    async def _root_children(self, root_id: str) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        cursor: str | None = None
        while True:
            query = f"?page_size=100&start_cursor={cursor}" if cursor else "?page_size=100"
            payload = await self._request("GET", f"/blocks/{root_id}/children{query}")
            for block in payload.get("results", []):
                block_type = block.get("type")
                if block_type not in {"child_page", "child_database"}:
                    continue
                title = block.get(block_type, {}).get("title")
                if title:
                    result[title] = {"type": block_type, "id": block["id"]}
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
        return result

    async def _create_dashboard(self, root_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/pages",
            json={
                "parent": {"type": "page_id", "page_id": root_id},
                "icon": {"type": "emoji", "emoji": "📈"},
                "properties": {"title": _text("Growly Dashboard")},
                "children": [
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {"rich_text": _text("Growly")},
                    },
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "icon": {"type": "emoji", "emoji": "ℹ️"},
                            "rich_text": _text(
                                "Content operations, market intelligence, approvals, "
                                "reports, and integration health in one workspace."
                            ),
                        },
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": _text("Operating workflow")},
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": _text(
                                "Manage sources, review market evidence, plan content, "
                                "approve drafts in Telegram, and track publication results."
                            )
                        },
                    },
                ],
            },
        )

    async def _database_data_source(self, database_id: str) -> str | None:
        database = await self._request("GET", f"/databases/{database_id}")
        data_sources = database.get("data_sources") or []
        return data_sources[0].get("id") if data_sources else None

    async def _create_database(
        self, root_id: str, name: str, properties: dict[str, Any]
    ) -> tuple[str, str]:
        database = await self._request(
            "POST",
            "/databases",
            json={
                "parent": {"type": "page_id", "page_id": root_id},
                "title": _text(name),
                "is_inline": False,
                "initial_data_source": {"properties": properties},
            },
        )
        database_id = database["id"]
        data_sources = database.get("data_sources") or []
        data_source_id = (
            data_sources[0].get("id")
            if data_sources
            else await self._database_data_source(database_id)
        )
        if not data_source_id:
            raise NotionServiceError(f"Notion did not return a data source for {name}.")
        return database_id, data_source_id

    async def _ensure_data_source_schema(
        self, data_source_id: str, properties: dict[str, Any]
    ) -> None:
        current = await self._request("GET", f"/data_sources/{data_source_id}")
        existing = current.get("properties") or {}
        missing = {
            name: definition
            for name, definition in properties.items()
            if name not in existing
        }
        if missing:
            await self._request(
                "PATCH",
                f"/data_sources/{data_source_id}",
                json={"properties": missing},
            )

    async def ensure_workspace(self) -> dict[str, str]:
        root_id = self.settings.require_text(
            "notion_root_page_id", "NOTION_ROOT_PAGE_ID"
        )
        await self.check_access()
        children = await self._root_children(root_id)
        saved: dict[str, str] = {}

        dashboard_id = await self._get_setting("notion_page_growly_dashboard")
        if not dashboard_id:
            child = children.get("Growly Dashboard")
            if child and child["type"] == "child_page":
                dashboard_id = child["id"]
            else:
                dashboard_id = (await self._create_dashboard(root_id))["id"]
        saved["notion_page_growly_dashboard"] = dashboard_id

        for name, properties in self.database_specs.items():
            slug = name.lower().replace(" ", "_").replace("&", "and")
            database_key = f"notion_database_{slug}"
            data_source_key = f"notion_data_source_{slug}"
            database_id = await self._get_setting(database_key)
            data_source_id = await self._get_setting(data_source_key)

            if not data_source_id:
                if not database_id:
                    child = children.get(name)
                    if child and child["type"] == "child_database":
                        database_id = child["id"]
                if database_id:
                    data_source_id = await self._database_data_source(database_id)
                else:
                    database_id, data_source_id = await self._create_database(
                        root_id, name, properties
                    )

            if not database_id or not data_source_id:
                raise NotionServiceError(f"Could not initialize Notion database {name}.")
            await self._ensure_data_source_schema(data_source_id, properties)
            saved[database_key] = database_id
            saved[data_source_key] = data_source_id

        await self._set_settings(saved)
        await self._ensure_dashboard_links(dashboard_id, saved)
        await self._sync_integration_status_rows()
        return saved

    async def _ensure_dashboard_links(
        self, dashboard_id: str, saved: dict[str, str]
    ) -> None:
        if await self._get_setting("notion_dashboard_links_v2") == "ready":
            return
        sections = [
            ("This Week Content Plan", "notion_database_content_calendar"),
            ("Pending Drafts", "notion_database_drafts"),
            ("Published Posts", "notion_database_publications"),
            ("Competitor Reports", "notion_database_reports"),
            ("Source Intelligence", "notion_database_source_items"),
            ("Review Insights", "notion_database_reviews_and_market_insights"),
            ("Performance Reports", "notion_database_reports"),
        ]
        children: list[dict[str, Any]] = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": _text("Intelligence workspace")},
            }
        ]
        for label, key in sections:
            database_id = saved.get(key)
            if not database_id:
                continue
            children.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": label,
                                    "link": {"url": self.page_url(database_id)},
                                },
                            }
                        ]
                    },
                }
            )
        await self._request(
            "PATCH",
            f"/blocks/{dashboard_id}/children",
            json={"children": children},
        )
        await self._set_settings({"notion_dashboard_links_v2": "ready"})

    async def _data_source_id(self, name: str) -> str:
        slug = name.lower().replace(" ", "_").replace("&", "and")
        value = await self._get_setting(f"notion_data_source_{slug}")
        if not value:
            raise NotionServiceError(
                "Notion workspace is not initialized. Run scripts/init_notion.py first."
            )
        return value

    async def _create_page(
        self,
        data_source_name: str,
        properties: dict[str, Any],
        *,
        body_text: str | None = None,
        icon: str = "📝",
    ) -> dict[str, Any]:
        data_source_id = await self._data_source_id(data_source_name)
        payload: dict[str, Any] = {
            "parent": {"type": "data_source_id", "data_source_id": data_source_id},
            "icon": {"type": "emoji", "emoji": icon},
            "properties": properties,
        }
        children = _paragraphs(body_text)
        if children:
            payload["children"] = children
        return await self._request("POST", "/pages", json=payload)

    async def _update_page(
        self, page_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH", f"/pages/{page_id}", json={"properties": properties}
        )

    async def archive_page(self, page_id: str) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/pages/{page_id}",
            json={"archived": True},
        )

    async def archive_database_row(
        self,
        data_source_name: str,
        row_id: int,
        *,
        page_id: str | None = None,
    ) -> bool:
        resolved_page_id = page_id
        if not resolved_page_id:
            existing = await self._query_number(
                data_source_name,
                "Supabase ID",
                row_id,
            )
            resolved_page_id = existing["id"] if existing else None
        if not resolved_page_id:
            return False
        await self.archive_page(resolved_page_id)
        return True

    async def _upsert_page(
        self,
        page_id: str | None,
        data_source_name: str,
        properties: dict[str, Any],
        *,
        body_text: str | None = None,
        icon: str = "📝",
    ) -> dict[str, Any]:
        if page_id:
            return await self._update_page(page_id, properties)
        return await self._create_page(
            data_source_name, properties, body_text=body_text, icon=icon
        )

    async def sync_source(self, source: Source) -> dict[str, Any]:
        return await self._upsert_page(
            source.notion_page_id,
            "Sources",
            {
                "Name": _title(source.name),
                "Type": _select(source.source_type),
                "URL": _url(source.url),
                "Category": _select(source.category),
                "Priority": _select(source.priority),
                "Status": _select(source.status),
                "Frequency": _select(source.check_frequency),
                "Last Checked": _date(source.last_checked_at),
                "Responsible": _rich_text(source.responsible),
                "Notes": _rich_text(source.notes),
                "Supabase ID": _number(source.id),
            },
            body_text=source.notes,
            icon="🔎",
        )

    async def sync_source_item(self, item: SourceItem) -> dict[str, Any]:
        existing = await self._query_number("Source Items", "Supabase ID", item.id)
        source_name = item.source_name
        if item.source_id:
            def load_source_name() -> str | None:
                with session_scope() as session:
                    source = session.get(Source, item.source_id)
                    return source.name if source else None

            source_name = await asyncio.to_thread(load_source_name)
        return await self._upsert_page(
            existing["id"] if existing else item.notion_page_id,
            "Source Items",
            {
                "Title": _title(item.title or item.topic or f"Source item {item.id}"),
                "URL": _url(item.url or item.external_url),
                "Provider": _select(item.source_provider),
                "Query": _rich_text(item.query),
                "Source Type": _select(item.source_type),
                "Snippet": _rich_text(item.snippet),
                "AI Summary": _rich_text(item.ai_summary),
                "Topics": _rich_text(self._list_text(item.topics_json)),
                "Offers": _rich_text(self._list_text(item.offers_json)),
                "CTAs": _rich_text(self._list_text(item.ctas_json)),
                "Pains": _rich_text(self._list_text(item.pains_json)),
                "Content Gaps": _rich_text(
                    self._list_text(item.content_gaps_json)
                ),
                "Status": _select(item.status),
                "Created At": _date(item.created_at),
                "Source": _rich_text(source_name),
                "Source ID": _number(item.source_id),
                "Topic": _rich_text(item.topic),
                "Format": _select(item.content_format),
                "Offer": _rich_text(item.offer),
                "CTA": _rich_text(item.cta),
                "Pain": _rich_text(item.audience_pain),
                "Hook": _rich_text(item.hook),
                "Summary": _rich_text(item.ai_summary),
                "Risk": _rich_text(item.risk_warning),
                "Adaptation Idea": _rich_text(item.adaptation_idea),
                "Supabase ID": _number(item.id),
            },
            body_text=(
                f"URL\n{item.url or item.external_url or ''}\n\n"
                f"Snippet\n{item.snippet or ''}\n\n"
                f"Content\n{item.content or item.raw_text or ''}\n\n"
                f"Engagement signals\n{item.engagement_signals_json or {}}"
            ),
            icon="🔬",
        )

    async def sync_content_plan(self, item: ContentPlan) -> dict[str, Any]:
        return await self._upsert_page(
            item.notion_page_id,
            "Content Calendar",
            {
                "Topic": _title(item.topic),
                "Publish Date": _date(item.publish_date),
                "Channel": _select(item.channel),
                "Content Type": _select(item.content_type),
                "Goal": _rich_text(item.goal),
                "Target Audience": _rich_text(item.target_audience),
                "CTA": _rich_text(item.cta),
                "Source Idea": _rich_text(item.source_idea),
                "Why Recommended": _rich_text(item.why_recommended),
                "Status": _select(item.status),
                "Supabase ID": _number(item.id),
            },
            body_text=(
                f"Key message\n{item.key_message or ''}\n\nCTA\n{item.cta or ''}\n\n"
                f"Source idea\n{item.source_idea or ''}"
            ),
            icon="🗓️",
        )

    async def sync_draft(self, draft: Draft) -> dict[str, Any]:
        return await self._upsert_page(
            draft.notion_page_id,
            "Drafts",
            {
                "Title": _title(draft.title or f"Draft {draft.id}"),
                "Status": _select(_status_label(draft.status)),
                "Version": _number(draft.version),
                "Channel": _select(draft.channel),
                "Type": _select(draft.draft_type),
                "Draft Text": _rich_text(draft.draft_text),
                "Prompt": _rich_text(draft.prompt_name),
                "AI Model": _rich_text(draft.ai_model),
                "Content Plan ID": _number(draft.content_plan_id),
                "Supabase ID": _number(draft.id),
            },
            body_text=draft.draft_text,
            icon="✍️",
        )

    async def sync_report(self, report: Report) -> dict[str, Any]:
        return await self._upsert_page(
            report.notion_page_id,
            "Reports",
            {
                "Title": _title(report.title),
                "Report Type": _select(report.report_type),
                "Query": _rich_text(report.query),
                "Sources Count": _number(report.sources_count),
                "Created At": _date(report.created_at),
                "Type": _select(report.report_type),
                "Week Start": _date(report.week_start),
                "Week End": _date(report.week_end),
                "Status": _select(report.status),
                "Report Text": _rich_text(report.report_text),
                "Summary": _rich_text(report.summary),
                "Recommendations": _rich_text(
                    "\n".join(map(str, report.recommendations_json or []))
                ),
                "Supabase ID": _number(report.id),
            },
            body_text=report.body or report.report_text,
            icon="📊",
        )

    @staticmethod
    def _list_text(value: list[Any] | None) -> str:
        return "\n".join(map(str, value or []))

    async def sync_review(self, review: ReviewImport) -> dict[str, Any]:
        pains = "\n".join(map(str, review.pains_json or []))
        objections = "\n".join(map(str, review.objections_json or []))
        ideas = "\n".join(map(str, review.content_ideas_json or []))
        return await self._upsert_page(
            review.notion_page_id,
            "Reviews and Market Insights",
            {
                "Title": _title(review.title),
                "Source": _rich_text(review.source_name),
                "Summary": _rich_text(review.ai_summary),
                "Pains": _rich_text(pains),
                "Objections": _rich_text(objections),
                "Content Ideas": _rich_text(ideas),
                "Supabase ID": _number(review.id),
            },
            body_text=(
                f"Summary\n{review.ai_summary or ''}\n\nPains\n{pains}\n\n"
                f"Objections\n{objections}\n\nContent opportunities\n{ideas}"
            ),
            icon="💬",
        )

    async def sync_publication(self, publication: Publication) -> dict[str, Any]:
        existing = await self._query_number(
            "Publications", "Supabase ID", publication.id
        )
        return await self._upsert_page(
            existing["id"] if existing else None,
            "Publications",
            {
                "Title": _title(f"Publication {publication.id}"),
                "Channel": _select(publication.channel),
                "Status": _select(_status_label(publication.status)),
                "Published URL": _url(publication.published_url),
                "Published At": _date(publication.published_at),
                "Views": _number(publication.views),
                "Reactions": _number(publication.reactions),
                "Comments": _number(publication.comments_count),
                "Clicks": _number(publication.clicks),
                "Leads": _number(publication.leads),
                "Telegram Message ID": _rich_text(publication.telegram_message_id),
                "Notes": _rich_text(publication.notes),
                "Supabase ID": _number(publication.id),
            },
            body_text=str(publication.metrics_json or {}),
            icon="📣",
        )

    async def _query_title(
        self, data_source_name: str, title_property: str, value: str
    ) -> dict[str, Any] | None:
        data_source_id = await self._data_source_id(data_source_name)
        result = await self._request(
            "POST",
            f"/data_sources/{data_source_id}/query",
            json={
                "page_size": 1,
                "filter": {
                    "property": title_property,
                    "title": {"equals": value},
                },
            },
        )
        rows = result.get("results") or []
        return rows[0] if rows else None

    async def _query_number(
        self, data_source_name: str, number_property: str, value: int
    ) -> dict[str, Any] | None:
        data_source_id = await self._data_source_id(data_source_name)
        result = await self._request(
            "POST",
            f"/data_sources/{data_source_id}/query",
            json={
                "page_size": 1,
                "filter": {
                    "property": number_property,
                    "number": {"equals": value},
                },
            },
        )
        rows = result.get("results") or []
        return rows[0] if rows else None

    async def _sync_integration_status_rows(self) -> None:
        integrations = [
            ("Supabase", "configured", "Primary technical database"),
            (
                "GitHub Models",
                (
                    "configured"
                    if (
                        self.settings.github_models_token
                        and self.settings.github_models_token.get_secret_value().strip()
                    )
                    else "disabled"
                ),
                "Primary AI text generation",
            ),
            (
                "Groq",
                (
                    "configured"
                    if (
                        self.settings.groq_api_key
                        and self.settings.groq_api_key.get_secret_value().strip()
                    )
                    else "disabled"
                ),
                "Fallback AI text generation",
            ),
            (
                "Tavily",
                "configured"
                if (self.settings.search_provider or "").lower() == "tavily"
                else "disabled",
                "Public web search and source discovery",
            ),
            ("Telegram", "configured", "Commands, approvals, and delivery"),
            ("Notion", "connected", "Client-facing workspace"),
            (
                "Instagram",
                "disabled" if not self.settings.instagram_enabled else "pending",
                "Future official API module",
            ),
            (
                "Bitrix24",
                "disabled" if not self.settings.bitrix_enabled else "pending",
                "Future CRM module",
            ),
            (
                "ERPNext",
                "disabled" if not self.settings.erpnext_enabled else "pending",
                "Future ERP module",
            ),
        ]
        now = datetime.now(UTC)
        for name, status, details in integrations:
            properties = {
                "Integration": _title(name),
                "Status": _select(status),
                "Details": _rich_text(details),
                "Last Checked": _date(now),
            }
            existing = await self._query_title(
                "Integration Status", "Integration", name
            )
            if existing:
                await self._update_page(existing["id"], properties)
            else:
                await self._create_page(
                    "Integration Status", properties, icon="🔌"
                )

    @staticmethod
    def page_url(page_id: str) -> str:
        return f"https://www.notion.so/{page_id.replace('-', '')}"

    async def sync_recent_data(
        self, limit: int = 25, workspace_id: str | None = None
    ) -> dict[str, int]:
        def load() -> dict[str, list[Any]]:
            with session_scope() as session:
                def scoped(statement: Any, model: Any) -> Any:
                    if workspace_id is None:
                        return statement
                    return statement.where(model.workspace_id == workspace_id)

                return {
                    "sources": list(
                        session.scalars(
                            scoped(
                                select(Source)
                                .order_by(desc(Source.updated_at))
                                .limit(limit),
                                Source,
                            )
                        )
                    ),
                    "content": list(
                        session.scalars(
                            scoped(
                                select(ContentPlan)
                                .order_by(desc(ContentPlan.updated_at))
                                .limit(limit),
                                ContentPlan,
                            )
                        )
                    ),
                    "source_items": list(
                        session.scalars(
                            scoped(
                                select(SourceItem)
                                .order_by(desc(SourceItem.collected_at))
                                .limit(limit),
                                SourceItem,
                            )
                        )
                    ),
                    "drafts": list(
                        session.scalars(
                            scoped(
                                select(Draft)
                                .order_by(desc(Draft.updated_at))
                                .limit(limit),
                                Draft,
                            )
                        )
                    ),
                    "reports": list(
                        session.scalars(
                            scoped(
                                select(Report)
                                .order_by(desc(Report.created_at))
                                .limit(limit),
                                Report,
                            )
                        )
                    ),
                    "reviews": list(
                        session.scalars(
                            scoped(
                                select(ReviewImport)
                                .order_by(desc(ReviewImport.created_at))
                                .limit(limit),
                                ReviewImport,
                            )
                        )
                    ),
                    "publications": list(
                        session.scalars(
                            scoped(
                                select(Publication)
                                .order_by(desc(Publication.updated_at))
                                .limit(limit),
                                Publication,
                            )
                        )
                    ),
                }

        rows = await asyncio.to_thread(load)
        counts = {key: 0 for key in rows}
        sync_map = {
            "sources": self.sync_source,
            "content": self.sync_content_plan,
            "source_items": self.sync_source_item,
            "drafts": self.sync_draft,
            "reports": self.sync_report,
            "reviews": self.sync_review,
            "publications": self.sync_publication,
        }
        for key, items in rows.items():
            for item in items:
                page = await sync_map[key](item)
                counts[key] += 1
                if not getattr(item, "notion_page_id", None):
                    await self._persist_page_id(type(item), item.id, page["id"])
        await self._set_settings(
            {
                "notion_last_sync_counts": json.dumps(counts),
                "notion_last_sync_at": datetime.now(UTC).isoformat(),
            },
            workspace_id=workspace_id,
        )
        return counts

    async def configured_database_links(self) -> dict[str, str]:
        key_map = {
            "Source Items": "notion_database_source_items",
            "Reports": "notion_database_reports",
            "Content Calendar": "notion_database_content_calendar",
        }

        def load() -> dict[str, str]:
            with session_scope() as session:
                values = SettingsRepository(session).get_many(
                    list(key_map.values())
                )
                return {
                    label: self.page_url(str(values[key]))
                    for label, key in key_map.items()
                    if values.get(key)
                }

        return await asyncio.to_thread(load)

    async def debug_status(self) -> dict[str, Any]:
        database_keys = [
            f"notion_database_{name.lower().replace(' ', '_').replace('&', 'and')}"
            for name in self.database_specs
        ]

        def load() -> dict[str, Any]:
            with session_scope() as session:
                repo = SettingsRepository(session)
                configured = repo.get_many(database_keys)
                last_sync_raw = repo.get("notion_last_sync_counts")
                try:
                    last_sync = json.loads(last_sync_raw or "{}")
                except json.JSONDecodeError:
                    last_sync = {}
                latest_report_id = session.scalar(
                    select(Report.id)
                    .order_by(desc(Report.created_at))
                    .limit(1)
                )
                return {
                    "notion_root_page_id": (
                        self.settings.notion_root_page_id or ""
                    ),
                    "database_ids": {
                        key: value
                        for key, value in configured.items()
                        if value
                    },
                    "supabase_counts": {
                        "source_items": int(
                            session.scalar(select(func.count(SourceItem.id)))
                            or 0
                        ),
                        "reports": int(
                            session.scalar(select(func.count(Report.id))) or 0
                        ),
                        "content_plan": int(
                            session.scalar(select(func.count(ContentPlan.id)))
                            or 0
                        ),
                        "drafts": int(
                            session.scalar(select(func.count(Draft.id))) or 0
                        ),
                        "publications": int(
                            session.scalar(
                                select(func.count(Publication.id))
                            )
                            or 0
                        ),
                    },
                    "latest_sync_counts": last_sync,
                    "latest_report_id": latest_report_id,
                    "latest_content_plan_count": int(
                        session.scalar(select(func.count(ContentPlan.id))) or 0
                    ),
                }

        return await asyncio.to_thread(load)

    async def _persist_page_id(
        self, model_type: type[Any], row_id: int, page_id: str
    ) -> None:
        def write() -> None:
            with session_scope() as session:
                row = session.get(model_type, row_id)
                if row is not None and hasattr(row, "notion_page_id"):
                    row.notion_page_id = page_id

        await asyncio.to_thread(write)
