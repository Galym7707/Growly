from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AppLog
from app.utils.logging import redact


class LogsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        level: str,
        module: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> AppLog:
        row = AppLog(
            level=level,
            module=module,
            message=str(redact(message)),
            details_json=redact(details or {}),
        )
        self.session.add(row)
        self.session.flush()
        return row

