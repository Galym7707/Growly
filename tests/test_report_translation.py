from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services.report_service import ReportService


class FailingAI:
    async def generate_text(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("cached report translations must not call AI")


@pytest.mark.asyncio
async def test_localized_report_uses_cached_translation() -> None:
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=1,
        report_type="market_scan",
        title="РђРЅР°Р»РёР· СЂС‹РЅРєР°",
        report_text="РўРµРєСЃС‚",
        body="РўРµРєСЃС‚",
        summary="РљСЂР°С‚РєРёР№ РІС‹РІРѕРґ",
        query="СЂС‹РЅРѕРє",
        sources_count=1,
        evidence_json=["https://example.com"],
        recommendations_json=["РџСЂРѕРІРµСЂРёС‚СЊ РѕС„С„РµСЂ"],
        raw_json={
            "language": "ru",
            "audience_pains": ["РќРµС‚ РІСЂРµРјРµРЅРё"],
            "translations": {
                "en": {
                    "title": "Market analysis",
                    "body": "Translated body",
                    "summary": "Short conclusion",
                    "query": "market",
                    "structure": {
                        "language": "ru",
                        "audience_pains": ["No time"],
                    },
                    "recommendations": ["Check the offer"],
                }
            },
        },
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        workspace_id="ws-a",
        created_at=now,
        updated_at=now,
    )

    localized = await ReportService(ai=FailingAI()).localized_report(report, "en")

    assert localized.title == "Market analysis"
    assert localized.summary == "Short conclusion"
    assert localized.body == "Translated body"
    assert localized.raw_json["audience_pains"] == ["No time"]
    assert "translations" not in localized.raw_json
    assert report.summary == "РљСЂР°С‚РєРёР№ РІС‹РІРѕРґ"
