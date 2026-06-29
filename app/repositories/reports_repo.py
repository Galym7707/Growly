from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload, load_only

from app.models import Approval, ContentPlan, Draft, Publication, Report, ReviewImport


def _report_summary_columns():
    return load_only(
        Report.id,
        Report.report_type,
        Report.title,
        Report.summary,
        Report.query,
        Report.sources_count,
        Report.week_start,
        Report.week_end,
        Report.status,
        Report.notion_page_id,
        Report.workspace_id,
        Report.created_at,
        Report.updated_at,
    )


class ReportsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_report(
        self,
        *,
        report_type: str,
        title: str,
        report_text: str,
        week_start: date | None = None,
        week_end: date | None = None,
        summary: str | None = None,
        recommendations: list[Any] | None = None,
        query: str | None = None,
        sources_count: int = 0,
        evidence: list[Any] | None = None,
        raw_json: dict[str, Any] | None = None,
        status: str = "ready",
    ) -> Report:
        report = Report(
            report_type=report_type,
            title=title,
            report_text=report_text,
            body=report_text,
            week_start=week_start,
            week_end=week_end,
            summary=summary,
            query=query,
            sources_count=sources_count,
            evidence_json=evidence or [],
            recommendations_json=recommendations or [],
            raw_json=raw_json,
            status=status,
        )
        self.session.add(report)
        self.session.flush()
        return report

    def get_report(self, report_id: int) -> Report | None:
        return self.session.get(Report, report_id)

    def set_report_notion_page(self, report: Report, notion_page_id: str) -> Report:
        report.notion_page_id = notion_page_id
        self.session.flush()
        return report

    def list_latest(self, limit: int = 10) -> list[Report]:
        return list(
            self.session.scalars(
                select(Report).order_by(desc(Report.created_at)).limit(limit)
            )
        )

    def list_latest_summary(self, limit: int = 10) -> list[Report]:
        return list(
            self.session.scalars(
                select(Report)
                .options(_report_summary_columns())
                .order_by(desc(Report.created_at))
                .limit(limit)
            )
        )

    def latest_report(self, report_type: str) -> Report | None:
        return self.session.scalar(
            select(Report)
            .where(Report.report_type == report_type)
            .order_by(desc(Report.created_at))
            .limit(1)
        )

    def latest_report_summary(self, report_type: str) -> Report | None:
        return self.session.scalar(
            select(Report)
            .options(_report_summary_columns())
            .where(Report.report_type == report_type)
            .order_by(desc(Report.created_at))
            .limit(1)
        )

    def latest_report_with_status(
        self,
        report_type: str,
        status: str,
    ) -> Report | None:
        return self.session.scalar(
            select(Report)
            .where(
                Report.report_type == report_type,
                Report.status == status,
            )
            .order_by(desc(Report.created_at))
            .limit(1)
        )

    def update_report(
        self,
        report: Report,
        *,
        report_text: str,
        summary: str,
        sources_count: int,
        evidence: list[Any],
        recommendations: list[Any],
        raw_json: dict[str, Any],
        status: str,
    ) -> Report:
        report.report_text = report_text
        report.body = report_text
        report.summary = summary
        report.sources_count = sources_count
        report.evidence_json = evidence
        report.recommendations_json = recommendations
        report.raw_json = raw_json
        report.status = status
        self.session.flush()
        return report

    def create_content_plan_item(self, payload: dict[str, Any]) -> ContentPlan:
        item = ContentPlan(**payload)
        self.session.add(item)
        self.session.flush()
        return item

    def set_content_plan_notion_page(
        self, item: ContentPlan, notion_page_id: str
    ) -> ContentPlan:
        item.notion_page_id = notion_page_id
        self.session.flush()
        return item

    def create_review_import(
        self,
        *,
        title: str,
        source_name: str,
        raw_text: str,
        ai_summary: str,
        pains: list[Any],
        objections: list[Any],
        content_ideas: list[Any],
        repeated_questions: list[Any] | None = None,
        trust_issues: list[Any] | None = None,
        buying_triggers: list[Any] | None = None,
        emotional_words: list[Any] | None = None,
        customer_language: list[Any] | None = None,
        faq_ideas: list[Any] | None = None,
        risk_notes: list[Any] | None = None,
        recommended_posts: list[Any] | None = None,
    ) -> ReviewImport:
        review = ReviewImport(
            title=title,
            source_name=source_name,
            raw_text=raw_text,
            ai_summary=ai_summary,
            pains_json=pains,
            objections_json=objections,
            content_ideas_json=content_ideas,
            repeated_questions_json=repeated_questions or [],
            trust_issues_json=trust_issues or [],
            buying_triggers_json=buying_triggers or [],
            emotional_words_json=emotional_words or [],
            customer_language_json=customer_language or [],
            faq_ideas_json=faq_ideas or [],
            risk_notes_json=risk_notes or [],
            recommended_posts_json=recommended_posts or [],
        )
        self.session.add(review)
        self.session.flush()
        return review

    def set_review_notion_page(
        self, review: ReviewImport, notion_page_id: str
    ) -> ReviewImport:
        review.notion_page_id = notion_page_id
        self.session.flush()
        return review

    def performance_counts(
        self, start: datetime, end: datetime
    ) -> dict[str, int]:
        def count_drafts(status: str | None = None) -> int:
            statement = select(func.count(Draft.id)).where(
                Draft.created_at >= start, Draft.created_at < end
            )
            if status:
                statement = statement.where(Draft.status == status)
            return int(self.session.scalar(statement) or 0)

        published = int(
            self.session.scalar(
                select(func.count(Publication.id)).where(
                    Publication.published_at >= start,
                    Publication.published_at < end,
                    Publication.status == "published",
                )
            )
            or 0
        )
        approved = int(
            self.session.scalar(
                select(func.count(Approval.id)).where(
                    Approval.created_at >= start,
                    Approval.created_at < end,
                    Approval.action == "approve",
                )
            )
            or 0
        )
        rejected = int(
            self.session.scalar(
                select(func.count(Approval.id)).where(
                    Approval.created_at >= start,
                    Approval.created_at < end,
                    Approval.action == "reject",
                )
            )
            or 0
        )
        return {
            "drafts": count_drafts(),
            "approved": approved,
            "rejected": rejected,
            "published": published,
        }

    def list_publications_for_period(
        self, start: datetime, end: datetime
    ) -> list[Publication]:
        return list(
            self.session.scalars(
                select(Publication)
                .where(Publication.created_at >= start, Publication.created_at < end)
                .order_by(desc(Publication.views))
            )
        )

    def list_recent_publications(self, limit: int = 20) -> list[Publication]:
        return list(
            self.session.scalars(
                select(Publication)
                .options(joinedload(Publication.draft))
                .where(Publication.status == "published")
                .order_by(desc(Publication.published_at), desc(Publication.created_at))
                .limit(limit)
            )
        )

    def get_publication(self, publication_id: int) -> Publication | None:
        return self.session.scalar(
            select(Publication)
            .options(joinedload(Publication.draft))
            .where(Publication.id == publication_id)
        )

    def schedule_publication(
        self, *, draft_id: int, when: datetime, channel: str = "Telegram"
    ) -> Publication:
        publication = Publication(
            draft_id=draft_id,
            channel=channel,
            status="scheduled",
            scheduled_for=when,
            metrics_json={},
        )
        self.session.add(publication)
        self.session.flush()
        return publication

    def list_due_scheduled(self, now: datetime, limit: int = 20) -> list[Publication]:
        statement = (
            select(Publication)
            .where(Publication.status == "scheduled")
            .where(Publication.scheduled_for <= now)
            .order_by(Publication.scheduled_for)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def update_publication_metrics(
        self,
        publication: Publication,
        *,
        views: int,
        reactions: int,
        comments: int,
        clicks: int,
        leads: int,
        notes: str | None,
    ) -> Publication:
        publication.views = views
        publication.reactions = reactions
        publication.comments_count = comments
        publication.clicks = clicks
        publication.leads = leads
        publication.notes = notes
        publication.metrics_json = {
            **(publication.metrics_json or {}),
            "views": views,
            "reactions": reactions,
            "comments": comments,
            "clicks": clicks,
            "leads": leads,
            "notes": notes or "",
        }
        self.session.flush()
        return publication

    def list_draft_plan_items(self, limit: int = 20) -> list[ContentPlan]:
        return list(
            self.session.scalars(
                select(ContentPlan)
                .where(ContentPlan.status == "draft")
                .order_by(ContentPlan.publish_date, ContentPlan.id)
                .limit(limit)
            )
        )

    def get_content_plan_item(self, item_id: int) -> ContentPlan | None:
        return self.session.get(ContentPlan, item_id)
