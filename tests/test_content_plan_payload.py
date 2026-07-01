from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.models import ContentPlan, Report, SourceItem
from app.services.content_plan_service import (
    CONTENT_PLAN_MAX_SNIPPET_CHARS,
    ContentPlanService,
)
from app.services.groq_service import GroqService
from app.utils.errors import AIServiceError


def plan_payload() -> str:
    start = datetime.now(UTC).replace(microsecond=0)
    rows: list[dict[str, Any]] = []
    formats = [
        ("Telegram", "post"),
        ("Instagram", "post"),
        ("Telegram", "educational post"),
        ("Instagram", "pain-point post"),
        ("Telegram", "comparison post"),
        ("Instagram", "Reels"),
        ("Instagram", "short video"),
        ("WhatsApp", "message"),
        ("Telegram", "weekly digest"),
    ]
    for index, (channel, content_type) in enumerate(formats):
        rows.append(
            {
                "publish_date": (start + timedelta(days=index)).isoformat(),
                "channel": channel,
                "content_type": content_type,
                "topic": f"Topic {index}",
                "goal": "Trust",
                "target_audience": "Small business",
                "key_message": "Evidence-based message",
                "cta": "Learn more",
                "source_idea": "https://example.com/evidence",
                "why_recommended": "Supported by saved public evidence.",
            }
        )
    return json.dumps(rows)


def source_items(count: int) -> list[SourceItem]:
    return [
        SourceItem(
            id=index,
            title=f"Source {index}",
            url=f"https://example.com/{index}",
            snippet="S" * 2000,
            raw_json={"secret_payload": "must not reach Groq"},
            topics_json=["Topic"],
            pains_json=["Pain"],
            content_gaps_json=["Gap"],
        )
        for index in range(1, count + 1)
    ]


class FakeNotion:
    async def sync_content_plan(
        self,
        item: ContentPlan,
    ) -> dict[str, str]:
        return {"id": f"page-{item.id}"}


def test_market_context_keeps_report_metadata_and_saved_source_set() -> None:
    report = Report(
        id=77,
        report_type="market_scan",
        title="Анализ рынка",
        query="ПП-рационы в Алматы",
        sources_count=2,
        evidence_json=[
            "https://example.com/one",
            "https://example.com/two",
        ],
        raw_json={
            "source_item_ids": [11, 12],
            "market_context": {
                "topic": "ПП-рационы в Алматы",
                "region": "Алматы",
                "language": "ru",
                "category": "доставка здорового и правильного питания",
                "category_code": "healthy_food_delivery",
                "region_language": "Алматы, русский",
            },
        },
    )

    context = ContentPlanService._market_context_from_report(report)

    assert context == {
        "topic": "ПП-рационы в Алматы",
        "region": "Алматы",
        "language": "ru",
        "category": "доставка здорового и правильного питания",
        "category_code": "healthy_food_delivery",
        "region_language": "Алматы, русский",
        "report_id": 77,
        "source_item_ids": [11, 12],
        "source_urls": [
            "https://example.com/one",
            "https://example.com/two",
        ],
        "sources_count": 2,
    }


@pytest.mark.asyncio
async def test_content_plan_with_33_sources_uses_batches_without_raw_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeGroq:
        def __init__(self) -> None:
            self.batch_contexts: list[dict[str, Any]] = []
            self.final_context: dict[str, Any] | None = None

        async def summarize_content_plan_sources(
            self,
            context: dict[str, Any],
        ) -> str:
            self.batch_contexts.append(context)
            return json.dumps(
                {
                    "summary": "Batch summary",
                    "top_topics": ["Topic"],
                    "top_pains": ["Pain"],
                    "top_content_gaps": ["Gap"],
                    "content_ideas": ["Idea"],
                    "evidence_urls": [
                        row["url"] for row in context["source_items"]
                    ],
                }
            )

        async def generate_content_plan(
            self,
            context: dict[str, Any],
        ) -> str:
            self.final_context = context
            return plan_payload()

    groq = FakeGroq()
    service = ContentPlanService(  # type: ignore[arg-type]
        groq=groq,
        notion=FakeNotion(),
    )
    data = {
        "weekly_objective": {"goal": "Trust"},
        "business": {"niche": "Automation", "region": "Kazakhstan"},
        "latest_market_scan": {
            "summary": "Market summary",
            "top_topics": ["Topic"],
            "top_pains": ["Pain"],
            "top_content_gaps": ["Gap"],
        },
        "latest_competitor_report": {"summary": "Competitor summary"},
        "evidence_limited": False,
        "evidence_urls": [f"https://example.com/{index}" for index in range(20)],
        "source_items": source_items(33),
        "requirements": {},
    }
    saved_summaries: list[dict[str, Any]] = []

    monkeypatch.setattr(
        service,
        "_load_context_data",
        lambda business_context: data,
    )
    monkeypatch.setattr(
        service,
        "_save_batch_summaries",
        lambda summaries, items, workspace_id=None: saved_summaries.extend(summaries),
    )
    monkeypatch.setattr(
        service,
        "_save_plan_items",
        lambda rows, workspace_id=None: [
            ContentPlan(id=index, **row)
            for index, row in enumerate(rows, start=1)
        ],
    )
    monkeypatch.setattr(
        service,
        "_save_page_id",
        lambda item_id, page_id: None,
    )

    items = await service.generate_weekly_plan({"goal": "Trust"})

    assert len(items) == 9
    assert len(groq.batch_contexts) == 5
    assert len(saved_summaries) == 5
    assert all(
        len(context["source_items"]) <= 8
        for context in groq.batch_contexts
    )
    assert all(
        len(row["snippet"]) <= CONTENT_PLAN_MAX_SNIPPET_CHARS
        for context in groq.batch_contexts
        for row in context["source_items"]
    )
    assert "raw_json" not in repr(groq.batch_contexts)
    assert groq.final_context is not None
    assert groq.final_context["source_items"] == []
    assert len(groq.final_context["source_batch_summaries"]) == 5
    assert len(groq.final_context["evidence_urls"]) == 8
    assert "raw_json" not in repr(groq.final_context)


@pytest.mark.asyncio
async def test_content_plan_413_retries_with_report_summary_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeGroq:
        def __init__(self) -> None:
            self.contexts: list[dict[str, Any]] = []

        async def generate_content_plan(
            self,
            context: dict[str, Any],
        ) -> str:
            self.contexts.append(context)
            if len(self.contexts) == 1:
                raise AIServiceError("too large", status=413)
            return plan_payload()

    groq = FakeGroq()
    service = ContentPlanService(  # type: ignore[arg-type]
        groq=groq,
        notion=FakeNotion(),
    )
    monkeypatch.setattr(
        service,
        "_load_context_data",
        lambda business_context: {
            "weekly_objective": {"goal": "Trust"},
            "business": {"niche": "Automation"},
            "latest_market_scan": {"summary": "Market summary"},
            "latest_competitor_report": {"summary": "Competitor summary"},
            "evidence_limited": False,
            "evidence_urls": ["https://example.com/evidence"],
            "source_items": source_items(1),
            "requirements": {},
        },
    )
    monkeypatch.setattr(
        service,
        "_save_plan_items",
        lambda rows, workspace_id=None: [
            ContentPlan(id=index, **row)
            for index, row in enumerate(rows, start=1)
        ],
    )
    monkeypatch.setattr(
        service,
        "_save_page_id",
        lambda item_id, page_id: None,
    )

    await service.generate_weekly_plan()

    assert service.reduced_context_used
    assert len(groq.contexts) == 2
    assert "source_items" in groq.contexts[0]
    assert "source_items" not in groq.contexts[1]
    assert groq.contexts[1]["context_reduced_due_to_payload_limit"] is True


def test_global_groq_budget_removes_raw_json_and_truncates_context() -> None:
    context = GroqService._apply_prompt_budget(
        {
            "source_items": [
                {
                    "url": f"https://example.com/{index}",
                    "snippet": "S" * 1000,
                    "raw_json": {"payload": "remove"},
                }
                for index in range(20)
            ],
            "evidence_urls": [
                f"https://example.com/{index}" for index in range(20)
            ],
            "report_context": "R" * 10_000,
        }
    )

    assert len(context["source_items"]) == 8
    assert len(context["source_items"][0]["snippet"]) == 300
    assert "raw_json" not in repr(context)
    assert len(context["evidence_urls"]) == 10
    assert len(context["report_context"]) == 4000


def test_content_plan_old_dates_are_moved_to_current_window() -> None:
    items = [
        {
            "publish_date": datetime(2024, 9, 1, 9, 0),
            "channel": "Telegram",
            "content_type": "post",
            "topic": "Topic",
            "goal": "Goal",
            "target_audience": "Audience",
            "key_message": "Message",
            "cta": "CTA",
            "source_idea": "Internal data",
            "why_recommended": "Reason",
            "status": "draft",
        }
    ]

    normalized = ContentPlanService._ensure_current_plan_dates(items)

    assert normalized[0]["publish_date"].date() >= datetime.now().date()
