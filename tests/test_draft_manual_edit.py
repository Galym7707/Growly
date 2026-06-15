from __future__ import annotations

from types import SimpleNamespace

from app.repositories.drafts_repo import DraftsRepository


class FakeSession:
    def __init__(self) -> None:
        self.flushed = False

    def flush(self) -> None:
        self.flushed = True


def test_apply_manual_edit_bumps_version_and_resets_to_pending() -> None:
    draft = SimpleNamespace(
        draft_text="old text",
        version=2,
        status="approved",
        approved_by="Marketer",
        generation_metadata_json={"why_this_should_work": "keep me"},
    )
    repo = DraftsRepository(FakeSession())

    result = repo.apply_manual_edit(draft, "new edited text")

    assert result.draft_text == "new edited text"
    assert result.version == 3
    assert result.status == "pending"
    assert result.approved_by is None
    assert result.generation_metadata_json == {"why_this_should_work": "keep me"}
