from __future__ import annotations

from datetime import date

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.models import ContentTask


class TasksRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: int) -> ContentTask | None:
        return self.session.get(ContentTask, task_id)

    def list_for_workspace(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ContentTask]:
        statement = select(ContentTask).where(
            ContentTask.workspace_id == workspace_id
        )
        if status:
            statement = statement.where(ContentTask.status == status)
        # Open tasks first, soonest due date first, then newest.
        statement = statement.order_by(
            asc(ContentTask.status == "done"),
            asc(ContentTask.due_date.is_(None)),
            asc(ContentTask.due_date),
            desc(ContentTask.created_at),
        ).limit(limit)
        return list(self.session.scalars(statement))

    def create(
        self,
        *,
        workspace_id: str,
        title: str,
        description: str | None = None,
        source_type: str = "manual",
        source_id: int | None = None,
        assignee_email: str | None = None,
        status: str = "todo",
        priority: str = "medium",
        due_date: date | None = None,
        created_by: str | None = None,
    ) -> ContentTask:
        task = ContentTask(
            workspace_id=workspace_id,
            title=title,
            description=description,
            source_type=source_type,
            source_id=source_id,
            assignee_email=(assignee_email or None),
            status=status,
            priority=priority,
            due_date=due_date,
            created_by=created_by,
        )
        self.session.add(task)
        self.session.flush()
        return task

    def update(self, task: ContentTask, **fields: object) -> ContentTask:
        for key, value in fields.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        self.session.flush()
        return task

    def delete(self, task: ContentTask) -> None:
        self.session.delete(task)
        self.session.flush()
