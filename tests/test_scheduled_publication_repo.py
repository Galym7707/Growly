from __future__ import annotations

from datetime import datetime, timedelta, UTC

from app.repositories.reports_repo import ReportsRepository


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        ...


def test_schedule_publication_creates_scheduled_row() -> None:
    repo = ReportsRepository(FakeSession())
    when = datetime.now(UTC) + timedelta(hours=2)

    pub = repo.schedule_publication(draft_id=5, when=when, channel="Telegram")

    assert pub.draft_id == 5
    assert pub.status == "scheduled"
    assert pub.scheduled_for == when
    assert pub.channel == "Telegram"
