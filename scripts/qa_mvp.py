from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect
from telegram import Bot

from app.bot.handlers import publish_approved_draft
from app.config import get_settings
from app.database import get_engine, get_session_factory
from app.models import Approval, Base, ContentPlan, Draft, Publication, Source, SourceItem
from app.repositories.reports_repo import ReportsRepository
from app.services.content_plan_service import ContentPlanService
from app.services.draft_service import DraftService
from app.services.report_service import ReportService
from app.services.source_analysis_service import SourceAnalysisService


def result(name: str, passed: bool, detail: str = "") -> bool:
    suffix = f" ({detail})" if detail else ""
    print(f"{'PASS' if passed else 'FAIL'}: {name}{suffix}")
    return passed


def schema_checks() -> tuple[bool, bool]:
    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    expected = {table.name for table in Base.metadata.sorted_tables}
    tables_ok = result("1. Required tables exist", expected <= tables)
    columns_ok = True
    for table in Base.metadata.sorted_tables:
        actual = {row["name"] for row in inspector.get_columns(table.name)}
        required = {column.name for column in table.columns}
        columns_ok = columns_ok and required <= actual
    result("2. Required columns exist", columns_ok)
    return tables_ok, columns_ok


def notion_check() -> bool:
    required = {
        "notion_data_source_sources",
        "notion_data_source_source_items",
        "notion_data_source_content_calendar",
        "notion_data_source_drafts",
        "notion_data_source_reports",
        "notion_data_source_publications",
    }
    session = get_session_factory()()
    try:
        from app.models import Setting

        found = {
            row.key
            for row in session.query(Setting).filter(Setting.key.in_(required)).all()
            if row.value
        }
        return result("3. Notion database IDs exist", required <= found)
    finally:
        session.close()


def transactional_workflow_checks() -> list[bool]:
    session = get_session_factory()()
    transaction = session.begin()
    checks: list[bool] = []
    try:
        source = Source(
            name="QA temporary source",
            source_type="Other",
            priority="low",
            check_frequency="weekly",
            status="active",
        )
        session.add(source)
        session.flush()
        checks.append(result("4. Source can be created", bool(source.id)))

        item = SourceItem(
            source_id=source.id,
            source_name=source.name,
            source_type="manual",
            source_provider="manual",
            query="qa_manual_import",
            title="QA source item",
            url="",
            raw_text="QA manually supplied competitor observation.",
            content="QA manually supplied competitor observation.",
            ai_summary="QA summary",
            metrics_json={},
            engagement_signals_json={},
            tags_json=["qa"],
        )
        session.add(item)
        session.flush()
        checks.append(result("5. Source item can be imported", bool(item.id)))

        checks.append(
            result(
                "6. Competitor report workflow is callable",
                callable(SourceAnalysisService.generate_competitor_report),
            )
        )
        checks.append(
            result(
                "7. Content plan workflow is callable",
                callable(ContentPlanService.generate_weekly_plan),
            )
        )

        plan = ContentPlan(topic="QA plan item", status="draft")
        session.add(plan)
        session.flush()
        draft = Draft(
            content_plan_id=plan.id,
            draft_type="qa",
            channel="Telegram",
            title="QA draft",
            draft_text="QA draft text",
            status="approved",
            original_context_json={},
            generation_metadata_json={},
        )
        session.add(draft)
        session.flush()
        checks.append(result("8. Draft can be linked to content plan", bool(draft.id)))

        approval = Approval(draft_id=draft.id, action="approve")
        session.add(approval)
        session.flush()
        checks.append(result("9. Draft approval can be recorded", bool(approval.id)))

        publication = Publication(
            draft_id=draft.id,
            channel="Telegram",
            status="published",
            metrics_json={},
        )
        session.add(publication)
        session.flush()
        checks.append(
            result(
                "10. Telegram publication workflow is configured",
                bool(get_settings().telegram_publish_target())
                and callable(publish_approved_draft),
            )
        )

        ReportsRepository(session).update_publication_metrics(
            publication,
            views=1,
            reactions=1,
            comments=0,
            clicks=0,
            leads=0,
            notes="QA rollback",
        )
        checks.append(result("11. Publication metrics can be updated", publication.views == 1))
        checks.append(
            result(
                "12. Performance report workflow is callable",
                callable(ReportService.generate_weekly_performance_report),
            )
        )
        return checks
    finally:
        transaction.rollback()
        session.close()


async def live_publish(draft_id: int) -> bool:
    settings = get_settings()
    bot = Bot(settings.telegram_token())
    published, detail = await publish_approved_draft(
        bot, DraftService(settings=settings), draft_id
    )
    return result("Live Telegram publication", published, detail)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe Growly MVP QA. Temporary database rows are rolled back."
    )
    parser.add_argument(
        "--live-publish-draft-id",
        type=int,
        help="Explicitly publish an existing approved draft through the real Telegram flow.",
    )
    args = parser.parse_args()
    checks = [*schema_checks(), notion_check(), *transactional_workflow_checks()]
    if args.live_publish_draft_id is not None:
        checks.append(asyncio.run(live_publish(args.live_publish_draft_id)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
