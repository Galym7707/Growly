from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Approval, Draft, User


class DraftsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    def list_pending(self, limit: int = 20) -> list[Draft]:
        statement = (
            select(Draft)
            .where(Draft.status == "pending")
            .order_by(desc(Draft.created_at))
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_recent(self, limit: int = 50) -> list[Draft]:
        return list(
            self.session.scalars(
                select(Draft).order_by(desc(Draft.created_at)).limit(limit)
            )
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
