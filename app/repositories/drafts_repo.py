from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, load_only

from app.models import Approval, Draft, User
from app.services.workspace_service import DEFAULT_WORKSPACE_ID


def _draft_summary_columns():
    return load_only(
        Draft.id,
        Draft.content_plan_id,
        Draft.draft_type,
        Draft.channel,
        Draft.title,
        Draft.version,
        Draft.status,
        Draft.approved_by,
        Draft.notion_page_id,
        Draft.workspace_id,
        Draft.created_at,
        Draft.updated_at,
    )


class DraftsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _workspace_filter(workspace_id: str):
        if workspace_id == DEFAULT_WORKSPACE_ID:
            return or_(
                Draft.workspace_id == workspace_id,
                Draft.workspace_id.is_(None),
            )
        return Draft.workspace_id == workspace_id

    def create(
        self,
        *,
        draft_type: str,
        channel: str,
        title: str,
        draft_text: str,
        ai_model: str,
        prompt_name: str,
        original_context: dict[str, Any],
        generation_metadata: dict[str, Any] | None = None,
        content_plan_id: int | None = None,
    ) -> Draft:
        draft = Draft(
            content_plan_id=content_plan_id,
            draft_type=draft_type,
            channel=channel,
            title=title,
            draft_text=draft_text,
            ai_model=ai_model,
            prompt_name=prompt_name,
            original_context_json=original_context,
            generation_metadata_json=generation_metadata or {},
        )
        self.session.add(draft)
        self.session.flush()
        return draft

    def get(self, draft_id: int) -> Draft | None:
        return self.session.get(Draft, draft_id)

    def list_pending(
        self, limit: int = 20, workspace_id: str | None = None
    ) -> list[Draft]:
        statement = (
            select(Draft)
            .where(Draft.status == "pending")
            .order_by(desc(Draft.created_at))
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(self._workspace_filter(workspace_id))
        return list(self.session.scalars(statement))

    def list_pending_summary(
        self, limit: int = 20, workspace_id: str | None = None
    ) -> list[Draft]:
        statement = (
            select(Draft)
            .options(_draft_summary_columns())
            .where(Draft.status == "pending")
            .order_by(desc(Draft.created_at))
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(self._workspace_filter(workspace_id))
        return list(self.session.scalars(statement))

    def count_pending(self, workspace_id: str | None = None) -> int:
        statement = select(func.count(Draft.id)).where(Draft.status == "pending")
        if workspace_id is not None:
            statement = statement.where(self._workspace_filter(workspace_id))
        return int(
            self.session.scalar(statement)
            or 0
        )

    def latest_for_plan(self, content_plan_id: int) -> Draft | None:
        return self.session.scalar(
            select(Draft)
            .where(Draft.content_plan_id == content_plan_id)
            .order_by(desc(Draft.created_at))
            .limit(1)
        )

    def latest_ids_for_plans(
        self, content_plan_ids: list[int]
    ) -> dict[int, int]:
        """Map each content_plan_id to its most recent draft id (one query)."""
        if not content_plan_ids:
            return {}
        rows = self.session.execute(
            select(Draft.content_plan_id, Draft.id, Draft.status)
            .where(Draft.content_plan_id.in_(content_plan_ids))
            .order_by(desc(Draft.created_at))
        ).all()
        latest: dict[int, int] = {}
        for plan_id, draft_id, _status in rows:
            if plan_id is not None and plan_id not in latest:
                latest[plan_id] = draft_id
        return latest

    def list_recent(
        self, limit: int = 50, workspace_id: str | None = None
    ) -> list[Draft]:
        statement = select(Draft).order_by(desc(Draft.created_at)).limit(limit)
        if workspace_id is not None:
            statement = statement.where(self._workspace_filter(workspace_id))
        return list(
            self.session.scalars(statement)
        )

    def list_recent_summary(
        self, limit: int = 50, workspace_id: str | None = None
    ) -> list[Draft]:
        statement = (
            select(Draft)
            .options(_draft_summary_columns())
            .order_by(desc(Draft.created_at))
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(self._workspace_filter(workspace_id))
        return list(
            self.session.scalars(statement)
        )

    def set_telegram_message(self, draft: Draft, message_id: int) -> Draft:
        draft.telegram_message_id = str(message_id)
        self.session.flush()
        return draft

    def set_notion_page(self, draft: Draft, notion_page_id: str) -> Draft:
        draft.notion_page_id = notion_page_id
        self.session.flush()
        return draft

    def update_status(
        self, draft: Draft, status: str, approved_by: str | None = None
    ) -> Draft:
        draft.status = status
        if approved_by:
            draft.approved_by = approved_by
        self.session.flush()
        return draft

    def replace_generated_content(
        self,
        draft: Draft,
        draft_text: str,
        generation_metadata: dict[str, Any] | None = None,
    ) -> Draft:
        draft.draft_text = draft_text
        draft.version += 1
        draft.status = "pending"
        draft.approved_by = None
        if generation_metadata is not None:
            draft.generation_metadata_json = generation_metadata
        self.session.flush()
        return draft

    def apply_manual_edit(self, draft: Draft, draft_text: str) -> Draft:
        draft.draft_text = draft_text
        draft.version += 1
        draft.status = "pending"
        draft.approved_by = None
        self.session.flush()
        return draft

    def add_approval(
        self,
        *,
        draft: Draft,
        action: str,
        user: User | None,
        comment: str | None = None,
    ) -> Approval:
        approval = Approval(
            draft_id=draft.id,
            user_id=user.id if user else None,
            action=action,
            comment=comment,
        )
        self.session.add(approval)
        self.session.flush()
        return approval
