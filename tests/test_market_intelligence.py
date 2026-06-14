from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import Settings
from app.models import Report, Source, SourceItem
from app.repositories.reports_repo import ReportsRepository
from app.repositories.sources_repo import SourcesRepository
from app.search.base import SearchResult
from app.services.market_intelligence import (
    MARKET_ANALYSIS_BATCH_SIZE,
    MARKET_SCAN_PENDING_STATUS,
    MarketIntelligenceService,
)
from app.services.source_discovery_service import SourceDiscoveryService
from app.utils.errors import AIServiceError


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for index, value in enumerate(self.added, start=1):
            if getattr(value, "id", None) is None:
                value.id = index


def test_web_search_result_is_mapped_for_source_items() -> None:
    session = FakeSession()
    result = SearchResult(
        title="Competitor page",
        url="https://example.com/competitor",
        snippet="Offer and CTA",
        content=None,
        source_provider="tavily",
        query="competitor query",
        published_at="2026-05-01T10:00:00Z",
        score=0.9,
        raw_json={"title": "Competitor page"},
    )

    item = SourcesRepository(session).create_search_item(result)  # type: ignore[arg-type]

    assert item.query == "competitor query"
    assert item.url == "https://example.com/competitor"
    assert item.source_type == "web_search"
    assert item.source_provider == "tavily"
    assert item.raw_text == "Offer and CTA"


def test_market_scan_builds_three_to_five_queries() -> None:
    queries = MarketIntelligenceService.build_market_queries(
        niche="B2B automation",
        region_language="Kazakhstan Russian",
        competitor_keywords="Alpha, Beta",
    )
    assert len(queries) == 5
    assert any("competitors" in query for query in queries)
    assert any("market trends" in query for query in queries)
    assert any("customer problems" in query for query in queries)
    assert any("Alpha, Beta" in query for query in queries)


def test_market_scan_report_renderer_keeps_evidence_and_limitations() -> None:
    text = MarketIntelligenceService.render_market_scan_report(
        {
            "executive_summary": "Вывод",
            "dominant_topics": ["Тема"],
            "audience_pains": ["Боль"],
            "content_gaps": ["Пробел"],
            "risks_and_limitations": ["Данных мало"],
            "evidence_urls": ["https://example.com/source"],
        }
    )
    assert "Данных мало" in text
    assert "https://example.com/source" in text


def test_competitor_report_renderer_has_required_business_structure() -> None:
    payload = {
        "executive_summary": "Три конкурента повторяют один оффер.",
        "competitors": [
            {
                "competitor": "Alpha",
                "channel": "Website",
                "offer": "Audit",
                "price_value": "Не подтверждено",
                "content_style": "Guides",
                "cta": "Book a call",
                "strengths": "Clear offer",
                "weaknesses": "Few cases",
                "opportunity": "Show proof",
                "source_urls": ["https://example.com/alpha"],
            }
        ],
        "repeating_offers": ["Audit"],
        "repeating_ctas": ["Book a call"],
        "content_gaps": ["Detailed cases"],
        "recommended_positioning": ["Evidence-led"],
        "actions_this_week": ["Publish one case"],
        "source_urls": ["https://example.com/alpha"],
        "limitations": ["Public web evidence only"],
    }

    text = MarketIntelligenceService.render_competitor_report(payload)

    for heading in (
        "Executive summary",
        "Competitor table",
        "Repeating offers",
        "Repeating CTAs",
        "Content gaps",
        "Recommended positioning",
        "5 actions for this week",
        "Source URLs",
    ):
        assert heading in text
    assert "| Alpha | Website | Audit |" in text
    assert "https://example.com/alpha" in text


def test_competitor_report_rejects_rows_without_verified_urls() -> None:
    payload = MarketIntelligenceService._normalize_competitor_report(
        {
            "executive_summary": "Summary",
            "competitors": [
                {
                    "competitor": "Verified",
                    "source_urls": ["https://example.com/verified"],
                },
                {
                    "competitor": "Invented",
                    "source_urls": ["https://invented.example/profile"],
                },
            ],
            "source_urls": [
                "https://example.com/verified",
                "https://invented.example/profile",
            ],
        },
        ["https://example.com/verified"],
    )

    assert [row["competitor"] for row in payload["competitors"]] == ["Verified"]
    assert payload["source_urls"] == ["https://example.com/verified"]


def test_partial_market_scan_report_status_is_persisted() -> None:
    session = FakeSession()

    report = ReportsRepository(session).create_report(  # type: ignore[arg-type]
        report_type="market_scan",
        title="Market scan: test",
        report_text="Search results were saved.",
        status=MARKET_SCAN_PENDING_STATUS,
    )

    assert report.status == MARKET_SCAN_PENDING_STATUS


@pytest.mark.asyncio
async def test_market_scan_batches_saved_source_items() -> None:
    class FakeGroq:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        async def analyze_market_search(
            self,
            context: dict[str, Any],
        ) -> str:
            rows = context["source_items"]
            self.batch_sizes.append(len(rows))
            return json.dumps(
                {
                    "dominant_topics": [f"batch-{context['batch_number']}"],
                    "repeated_offers": [],
                    "repeated_ctas": [],
                    "audience_pains": [],
                    "objections": [],
                    "formats": [],
                    "content_gaps": [],
                    "risks": [],
                    "content_ideas": [],
                    "weekly_priorities": [],
                    "evidence_urls": [row["url"] for row in rows],
                    "source_items": [
                        {
                            "url": row["url"],
                            "ai_summary": row["title"],
                        }
                        for row in rows
                    ],
                }
            )

    groq = FakeGroq()
    service = MarketIntelligenceService(
        settings=Settings(_env_file=None),
        search_provider=SimpleNamespace(),
        groq=groq,  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )
    items = [
        SourceItem(
            id=index,
            title=f"Source {index}",
            url=f"https://example.com/{index}",
            snippet="Public evidence",
        )
        for index in range(1, MARKET_ANALYSIS_BATCH_SIZE * 2 + 2)
    ]

    analysis, summaries = await service._analyze_source_item_batches(
        "market query",
        items,
    )

    assert groq.batch_sizes == [
        MARKET_ANALYSIS_BATCH_SIZE,
        MARKET_ANALYSIS_BATCH_SIZE,
        1,
    ]
    assert len(analysis["source_items"]) == len(items)
    assert len(summaries) == 3


@pytest.mark.asyncio
async def test_market_scan_final_prompt_uses_compact_batch_summary() -> None:
    class CapturingGroq:
        def __init__(self) -> None:
            self.context: dict[str, Any] | None = None

        async def generate_market_scan(
            self,
            context: dict[str, Any],
        ) -> str:
            self.context = context
            return json.dumps(
                {
                    "executive_summary": "Summary",
                    "sources_checked": 1,
                    "dominant_topics": [],
                    "repeated_offers": [],
                    "repeated_ctas": [],
                    "audience_pains": [],
                    "objections": [],
                    "content_gaps": [],
                    "risks_and_limitations": [],
                    "content_ideas": [],
                    "weekly_priorities": [],
                    "evidence_urls": ["https://example.com/source"],
                }
            )

    groq = CapturingGroq()
    service = MarketIntelligenceService(
        settings=Settings(_env_file=None),
        search_provider=SimpleNamespace(),
        groq=groq,  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )

    await service.generate_market_scan_report(
        "test",
        [
            {
                "id": 1,
                "title": "Source",
                "url": "https://example.com/source",
                "snippet": "x" * 10_000,
                "content": "y" * 10_000,
                "ai_summary": "z" * 10_000,
            }
        ],
        batch_summaries=[
            {
                "dominant_topics": ["Topic"],
                "evidence_urls": ["https://example.com/source"],
            }
        ],
    )

    assert groq.context is not None
    assert "saved_source_item_batch_summary" in groq.context
    assert groq.context["source_evidence"] == [
        {
            "id": 1,
            "title": "Source",
            "url": "https://example.com/source",
        }
    ]
    assert "snippet" not in groq.context["source_evidence"][0]
    assert "content" not in groq.context["source_evidence"][0]


@pytest.mark.asyncio
async def test_retry_analysis_reuses_pending_report_source_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending = Report(
        id=41,
        report_type="market_scan",
        title="Pending scan",
        report_text="Pending",
        query="B2B automation",
        status=MARKET_SCAN_PENDING_STATUS,
        raw_json={"queries": ["query one"], "source_item_ids": [7]},
    )
    item = SourceItem(
        id=7,
        title="Saved source",
        url="https://example.com/saved",
        snippet="Evidence",
    )
    completed = Report(
        id=41,
        report_type="market_scan",
        title="Completed scan",
        report_text="Ready",
        query="B2B automation",
        status="ready",
        raw_json={"groq_status": "ready"},
    )
    captured: dict[str, Any] = {}
    service = MarketIntelligenceService(
        settings=Settings(_env_file=None),
        search_provider=SimpleNamespace(),
        groq=SimpleNamespace(),  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )

    monkeypatch.setattr(
        service,
        "_load_pending_scan",
        lambda report_id: (pending, [item]),
    )
    monkeypatch.setattr(service, "_job_id_for_report", lambda report_id: None)

    async def complete(**kwargs: Any) -> tuple[Report, list[SourceItem]]:
        captured.update(kwargs)
        return completed, kwargs["saved"]

    monkeypatch.setattr(service, "_complete_market_scan_analysis", complete)

    async def no_source_sync(items: list[SourceItem]) -> None:
        return None

    async def no_report_sync(report: Report) -> None:
        return None

    monkeypatch.setattr(service, "_sync_source_items", no_source_sync)
    monkeypatch.setattr(service, "_sync_report", no_report_sync)

    report, items = await service.retry_latest_analysis(41)

    assert report.status == "ready"
    assert items == [item]
    assert captured["existing_report_id"] == 41
    assert captured["queries"] == ["query one"]
    assert captured["saved"] == [item]


@pytest.mark.asyncio
async def test_market_scan_saves_before_groq_and_syncs_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    events: list[str] = []

    class FakeSearch:
        def search(
            self,
            query: str,
            max_results: int,
            *,
            include_raw_content: bool,
        ) -> list[SearchResult]:
            events.append("tavily")
            index = len([event for event in events if event == "tavily"])
            return [
                SearchResult(
                    title=f"Result {index}",
                    url=f"https://example.com/{index}",
                    snippet="Public result",
                    content=None,
                    source_provider="tavily",
                    query=query,
                    published_at=None,
                    score=0.8,
                    raw_json=None,
                )
            ]

    class RateLimitedGroq:
        async def analyze_market_search(
            self,
            context: dict[str, Any],
        ) -> str:
            events.append("groq")
            raise AIServiceError(
                "rate limited",
                status=429,
                retry_after=5,
            )

    class FakeNotion:
        async def sync_source_item(self, item: SourceItem) -> dict[str, str]:
            events.append(f"notion_item:{item.id}")
            return {"id": item.notion_page_id or f"page-{item.id}"}

        async def sync_report(self, report: Report) -> dict[str, str]:
            events.append("notion_report")
            return {"id": report.notion_page_id or "report-page"}

    service = MarketIntelligenceService(
        settings=Settings(_env_file=None, SEARCH_MAX_RESULTS=5),
        search_provider=FakeSearch(),  # type: ignore[arg-type]
        groq=RateLimitedGroq(),  # type: ignore[arg-type]
        notion=FakeNotion(),  # type: ignore[arg-type]
    )

    def save_results(results: list[SearchResult]) -> list[SourceItem]:
        events.append("save")
        return [
            SourceItem(
                id=index,
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                query=result.query,
                notion_page_id=f"page-{index}",
            )
            for index, result in enumerate(results, start=1)
        ]

    def save_partial(
        query: str,
        queries: list[str],
        source_items: list[SourceItem],
        groq_status: str,
    ) -> Report:
        events.append("partial_report")
        return Report(
            id=99,
            report_type="market_scan",
            title=f"Market scan: {query}",
            report_text="Search results were saved.",
            summary="Search results were saved.",
            query=query,
            sources_count=len(source_items),
            status=MARKET_SCAN_PENDING_STATUS,
            raw_json={
                "source_item_ids": [item.id for item in source_items],
                "queries": queries,
                "groq_status": groq_status,
            },
            notion_page_id="report-page",
        )

    monkeypatch.setattr(service, "_save_results", save_results)
    monkeypatch.setattr(service, "_save_partial_market_scan_report", save_partial)
    caplog.set_level(logging.INFO)
    progress_messages: list[str] = []

    async def progress(message: str) -> None:
        progress_messages.append(message)

    report, items = await service.run_market_scan(
        niche="B2B automation",
        region_language="Kazakhstan Russian",
        competitor_keywords="none",
        progress=progress,
    )

    groq_index = events.index("groq")
    notion_indexes = [
        index
        for index, event in enumerate(events)
        if event.startswith("notion_item:")
    ]
    assert len(items) == 4
    assert notion_indexes
    assert events.index("save") < groq_index
    assert min(notion_indexes) > groq_index
    assert report.status == MARKET_SCAN_PENDING_STATUS
    assert report.raw_json["groq_status"] == "rate_limited"
    assert "tavily_results_count=4" in caplog.text
    assert "source_items_saved_count=4" in caplog.text
    assert "market_scan_started" in caplog.text
    assert "tavily_query_started" in caplog.text
    assert "tavily_query_finished" in caplog.text
    assert "groq_analysis_started" in caplog.text
    assert "groq_analysis_failed" in caplog.text
    assert "notion_sync_started" in caplog.text
    assert "notion_sync_finished" in caplog.text
    assert "groq_status=rate_limited" in caplog.text
    assert f"report_status={MARKET_SCAN_PENDING_STATUS}" in caplog.text
    assert progress_messages[0] == "Шаг 1/5: ищу источники через Tavily..."
    assert "Шаг 2/5: найдено 4 результатов." in progress_messages
    assert "Шаг 3/5: сохраняю источники в Supabase..." in progress_messages
    assert (
        "Источники сохранены: 4. Даже если AI-анализ не завершится, "
        "данные уже не потеряются."
    ) in progress_messages
    assert "Шаг 4/5: анализирую источники через AI..." in progress_messages
    assert "Шаг 5/5: сохраняю отчет в Notion..." in progress_messages
    assert progress_messages[-1] == "Готово."


def test_source_discovery_builds_platform_specific_queries() -> None:
    queries = SourceDiscoveryService.build_discovery_queries(
        niche="construction",
        region="Kazakhstan",
        platforms=["Website", "Telegram", "Instagram", "TikTok", "YouTube"],
    )
    rendered = dict(queries)
    assert "official website" in rendered["Website"]
    assert "site:t.me" in rendered["Telegram"]
    assert "site:instagram.com" in rendered["Instagram"]
    assert "site:tiktok.com" in rendered["TikTok"]
    assert "site:youtube.com" in rendered["YouTube"]


def test_source_discovery_accepts_profiles_but_rejects_posts() -> None:
    assert SourceDiscoveryService.result_matches_platform(
        "https://example.com",
        "Website",
    )
    assert not SourceDiscoveryService.result_matches_platform(
        "https://instagram.com/example_company",
        "Website",
    )
    assert SourceDiscoveryService.result_matches_platform(
        "https://instagram.com/example_company",
        "Instagram",
    )
    assert not SourceDiscoveryService.result_matches_platform(
        "https://instagram.com/p/ABC123",
        "Instagram",
    )
    assert SourceDiscoveryService.result_matches_platform(
        "https://tiktok.com/@example",
        "TikTok",
    )
    assert not SourceDiscoveryService.result_matches_platform(
        "https://tiktok.com/@example/video/123",
        "TikTok",
    )
    assert SourceDiscoveryService.result_matches_platform(
        "https://youtube.com/@example",
        "YouTube",
    )
    assert not SourceDiscoveryService.result_matches_platform(
        "https://youtube.com/shorts/abc",
        "YouTube",
    )
    assert SourceDiscoveryService.result_matches_platform(
        "https://t.me/example_channel",
        "Telegram",
    )
    assert not SourceDiscoveryService.result_matches_platform(
        "https://t.me/example_channel/123",
        "Telegram",
    )


def test_monitoring_result_is_linked_to_active_source() -> None:
    session = FakeSession()
    source = Source(
        id=7,
        name="Example",
        source_type="Website",
        url="https://example.com",
        status="active",
    )
    result = SearchResult(
        title="Example update",
        url="https://example.com/news",
        snippet="Public update",
        content=None,
        source_provider="tavily",
        query='"Example" latest public information',
        published_at=None,
        score=0.7,
        raw_json=None,
    )

    item = SourcesRepository(session).create_monitoring_item(  # type: ignore[arg-type]
        source,
        result,
    )

    assert item.source_id == 7
    assert item.source_name == "Example"
    assert item.source_type == "source_monitoring"
    assert source.last_checked_at is not None


@pytest.mark.asyncio
async def test_source_extraction_rejects_invented_urls_and_post_links() -> None:
    class FakeGroq:
        async def extract_source_candidates(
            self, context: dict[str, Any]
        ) -> str:
            return """
            [
              {
                "name": "Allowed Profile",
                "url": "https://instagram.com/allowed",
                "platform": "instagram",
                "reason": "Official profile",
                "evidence_title": "Allowed"
              },
              {
                "name": "Invented",
                "url": "https://instagram.com/invented",
                "platform": "Instagram",
                "reason": "Not in evidence",
                "evidence_title": "Invented"
              },
              {
                "name": "Post",
                "url": "https://instagram.com/p/ABC123",
                "platform": "Instagram",
                "reason": "Post, not profile",
                "evidence_title": "Post"
              }
            ]
            """

    service = SourceDiscoveryService(
        settings=Settings(_env_file=None),
        search_provider=SimpleNamespace(),
        groq=FakeGroq(),  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )
    results = [
        SearchResult(
            title="Allowed",
            url="https://instagram.com/allowed",
            snippet="Official profile",
            content=None,
            source_provider="tavily",
            query="query",
            published_at=None,
            score=0.9,
            raw_json=None,
        ),
        SearchResult(
            title="Post",
            url="https://instagram.com/p/ABC123",
            snippet="A public post",
            content=None,
            source_provider="tavily",
            query="query",
            published_at=None,
            score=0.8,
            raw_json=None,
        ),
    ]

    candidates = await service._extract_candidates(
        niche="niche",
        region="region",
        platforms=["Instagram"],
        results=results,
    )

    assert candidates == [
        {
            "name": "Allowed Profile",
            "url": "https://instagram.com/allowed",
            "platform": "Instagram",
            "reason": "Official profile",
            "evidence_title": "Allowed",
        }
    ]
