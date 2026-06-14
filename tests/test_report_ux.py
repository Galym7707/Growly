from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.report_service import ReportService


def test_performance_data_requires_publications_and_metrics() -> None:
    assert not ReportService._has_useful_performance_data(
        {
            "counts": {"published": 0},
            "publication_metrics": [],
        }
    )
    assert not ReportService._has_useful_performance_data(
        {
            "counts": {"published": 1},
            "publication_metrics": [
                {
                    "views": None,
                    "reactions": None,
                    "comments": None,
                    "clicks": None,
                    "leads": None,
                }
            ],
        }
    )
    assert ReportService._has_useful_performance_data(
        {
            "counts": {"published": 1},
            "publication_metrics": [
                {
                    "views": 0,
                    "reactions": 0,
                    "comments": 0,
                    "clicks": 0,
                    "leads": 0,
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_empty_performance_data_does_not_call_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingAI:
        async def generate_weekly_performance_report(
            self,
            context: dict[str, object],
        ) -> str:
            raise AssertionError("ИИ не должен вызываться без метрик.")

    service = ReportService(
        groq=FailingAI(),  # type: ignore[arg-type]
        notion=SimpleNamespace(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        service,
        "_performance_context",
        lambda start, end: {
            "period": {"start": start.date(), "end": end.date()},
            "counts": {
                "drafts": 0,
                "approved": 0,
                "rejected": 0,
                "published": 0,
            },
            "publication_metrics": [],
        },
    )

    assert await service.generate_weekly_performance_report() is None
