from __future__ import annotations

import pytest

from app.services.weekly_cycle_service import WeeklyCycleService


@pytest.mark.asyncio
async def test_weekly_cycle_runs_in_order() -> None:
    order: list[str] = []

    class FakeSourceAnalysis:
        async def generate_competitor_report(self):
            order.append("competitor")

    class FakeContentPlan:
        async def generate_weekly_plan(self):
            order.append("content_plan")

    class FakeReport:
        async def generate_weekly_performance_report(self):
            order.append("performance")

    svc = WeeklyCycleService(
        source_analysis=FakeSourceAnalysis(),
        content_plan=FakeContentPlan(),
        report=FakeReport(),
    )
    await svc.run()

    assert order == ["competitor", "content_plan", "performance"]


@pytest.mark.asyncio
async def test_weekly_cycle_continues_if_a_step_fails() -> None:
    order: list[str] = []

    class Boom:
        async def generate_competitor_report(self):
            raise RuntimeError("boom")

    class FakeContentPlan:
        async def generate_weekly_plan(self):
            order.append("content_plan")

    class FakeReport:
        async def generate_weekly_performance_report(self):
            order.append("performance")

    svc = WeeklyCycleService(
        source_analysis=Boom(),
        content_plan=FakeContentPlan(),
        report=FakeReport(),
    )
    await svc.run()

    assert order == ["content_plan", "performance"]
