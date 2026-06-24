from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.workspace_service import (
    Membership,
    WorkspaceService,
    can_edit,
    can_manage_integrations,
    can_manage_team,
    can_publish,
    can_view,
    generate_token,
    hash_share_password,
    verify_share_password,
)
from app.web_api import current_membership


def _membership(role: str, workspace_id: str = "default") -> Membership:
    return Membership(
        member_id=1,
        workspace_id=workspace_id,
        email="user@example.com",
        role=role,
        status="active",
    )


def _no_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "growly_web_api_key", None)


@contextmanager
def _override_membership(membership: Membership | None):
    app.dependency_overrides[current_membership] = lambda: membership
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_membership, None)


# -- pure permission logic --------------------------------------------------


def test_role_permission_matrix() -> None:
    assert can_view("viewer") and can_view("owner")
    assert not can_edit("viewer")
    assert can_edit("editor") and can_edit("admin") and can_edit("owner")
    assert not can_publish("viewer")
    assert can_publish("editor")
    assert not can_manage_team("editor")
    assert can_manage_team("admin") and can_manage_team("owner")
    assert not can_manage_integrations("editor")
    assert can_manage_integrations("owner")


def test_generated_tokens_are_long_and_unique() -> None:
    first = generate_token()
    second = generate_token()
    assert len(first) >= 32
    assert first != second


def test_share_password_hash_roundtrip() -> None:
    stored = hash_share_password("s3cret")
    assert stored.startswith("pbkdf2$")
    assert verify_share_password("s3cret", stored)
    assert not verify_share_password("wrong", stored)
    # No password set means the link is open.
    assert verify_share_password("anything", None)


# -- cross-workspace isolation (acceptance #11) -----------------------------


def test_report_from_other_workspace_is_hidden(monkeypatch) -> None:
    _no_key(monkeypatch)

    async def get_report(self, report_id: int):
        return SimpleNamespace(workspace_id="default")

    monkeypatch.setattr("app.web_api.ReportService.get_report", get_report)

    with _override_membership(_membership("admin", workspace_id="ws-b")):
        response = TestClient(app).get("/api/reports/5")

    assert response.status_code == 404


def test_report_in_same_workspace_is_visible(monkeypatch) -> None:
    _no_key(monkeypatch)
    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=5,
        report_type="competitor_report",
        title="T",
        body="B",
        report_text="B",
        summary="S",
        query="q",
        sources_count=1,
        evidence_json=[],
        recommendations_json=[],
        raw_json={},
        week_start=None,
        week_end=None,
        status="ready",
        notion_page_id=None,
        workspace_id="ws-b",
        created_at=now,
        updated_at=now,
    )

    async def get_report(self, report_id: int):
        return report

    monkeypatch.setattr("app.web_api.ReportService.get_report", get_report)

    with _override_membership(_membership("admin", workspace_id="ws-b")):
        response = TestClient(app).get("/api/reports/5")

    assert response.status_code == 200
    assert response.json()["report"]["id"] == 5


# -- role enforcement on endpoints ------------------------------------------


def test_viewer_cannot_invite(monkeypatch) -> None:
    _no_key(monkeypatch)
    with _override_membership(_membership("viewer")):
        response = TestClient(app).post(
            "/api/workspaces/default/invitations",
            json={"email": "new@example.com", "role": "editor"},
        )
    assert response.status_code == 403


def test_viewer_cannot_create_task(monkeypatch) -> None:
    _no_key(monkeypatch)
    with _override_membership(_membership("viewer")):
        response = TestClient(app).post(
            "/api/tasks", json={"title": "Do the thing"}
        )
    assert response.status_code == 403


def test_invitation_for_other_workspace_is_denied(monkeypatch) -> None:
    _no_key(monkeypatch)
    with _override_membership(_membership("admin", workspace_id="ws-a")):
        response = TestClient(app).post(
            "/api/workspaces/ws-b/invitations",
            json={"email": "new@example.com", "role": "editor"},
        )
    assert response.status_code == 404


# -- happy paths with the DB layer faked ------------------------------------


def test_admin_can_create_invitation(monkeypatch) -> None:
    _no_key(monkeypatch)
    captured: dict = {}

    class FakeRepo:
        def __init__(self, session):
            del session

        def get_member_in_workspace(self, workspace_id, email):
            del workspace_id, email
            return None

        def create_invitation(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                id=1,
                workspace_id=kwargs["workspace_id"],
                email=kwargs["email"],
                role=kwargs["role"],
                token=kwargs["token"],
                status="pending",
                invited_by=kwargs["invited_by"],
                expires_at=kwargs["expires_at"],
                accepted_at=None,
                created_at=datetime.now(UTC),
            )

    @contextmanager
    def fake_session_scope():
        yield SimpleNamespace()

    monkeypatch.setattr("app.web_api.WorkspaceRepository", FakeRepo)
    monkeypatch.setattr("app.web_api.session_scope", fake_session_scope)

    with _override_membership(_membership("admin")):
        response = TestClient(app).post(
            "/api/workspaces/default/invitations",
            json={"email": "New@Example.com", "role": "editor"},
        )

    assert response.status_code == 200
    body = response.json()["invitation"]
    assert body["role"] == "editor"
    assert body["email"] == "new@example.com"
    assert body["invite_path"].startswith("/invite/")
    assert captured["email"] == "new@example.com"


def test_editor_can_create_task(monkeypatch) -> None:
    _no_key(monkeypatch)

    class FakeTasks:
        def __init__(self, session):
            del session

        def create(self, **kwargs):
            now = datetime.now(UTC)
            return SimpleNamespace(
                id=10,
                workspace_id=kwargs["workspace_id"],
                source_type=kwargs.get("source_type", "manual"),
                source_id=kwargs.get("source_id"),
                title=kwargs["title"],
                description=kwargs.get("description"),
                assignee_email=kwargs.get("assignee_email"),
                status=kwargs.get("status", "todo"),
                priority=kwargs.get("priority", "medium"),
                due_date=kwargs.get("due_date"),
                created_by=kwargs.get("created_by"),
                created_at=now,
                updated_at=now,
            )

    @contextmanager
    def fake_session_scope():
        yield SimpleNamespace()

    monkeypatch.setattr("app.web_api.TasksRepository", FakeTasks)
    monkeypatch.setattr("app.web_api.session_scope", fake_session_scope)

    with _override_membership(_membership("editor")):
        response = TestClient(app).post(
            "/api/tasks",
            json={"title": "Write captions", "priority": "high"},
        )

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["title"] == "Write captions"
    assert task["priority"] == "high"
    assert task["created_by"] == "user@example.com"


def test_invitation_accept_requires_matching_email(monkeypatch) -> None:
    _no_key(monkeypatch)

    class FakeRepo:
        def __init__(self, session):
            del session

        def get_invitation_by_token(self, token):
            del token
            return SimpleNamespace(
                workspace_id="default",
                email="invited@example.com",
                role="editor",
                status="pending",
                expires_at=datetime.now(UTC).replace(year=2999),
            )

    @contextmanager
    def fake_session_scope():
        yield SimpleNamespace()

    monkeypatch.setattr("app.web_api.WorkspaceRepository", FakeRepo)
    monkeypatch.setattr("app.web_api.session_scope", fake_session_scope)

    response = TestClient(app).post(
        "/api/invitations/tok123/accept",
        headers={"X-Growly-User-Email": "someone-else@example.com"},
    )
    assert response.status_code == 403


def test_resolve_service_denies_unknown_non_member(monkeypatch) -> None:
    """An authenticated user who is not a member and is not the bootstrap owner
    is denied (the default workspace already has an owner)."""

    class FakeRepo:
        def __init__(self, session):
            del session

        def get_active_member_by_email(self, email):
            del email
            return None

        def has_any_member(self, workspace_id):
            del workspace_id
            return True  # owner already exists

    @contextmanager
    def fake_session_scope():
        yield SimpleNamespace()

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository", FakeRepo
    )
    monkeypatch.setattr(
        "app.services.workspace_service.session_scope", fake_session_scope
    )

    assert WorkspaceService().resolve("stranger@example.com") is None


def test_content_plan_detail_from_other_workspace_is_hidden(monkeypatch) -> None:
    _no_key(monkeypatch)

    class FakeSession:
        def get(self, model, plan_id):
            del model, plan_id
            return SimpleNamespace(workspace_id="default")

    @contextmanager
    def fake_scope():
        yield FakeSession()

    monkeypatch.setattr("app.web_api.session_scope", fake_scope)

    with _override_membership(_membership("admin", workspace_id="ws-b")):
        response = TestClient(app).get("/api/content-plans/9")

    assert response.status_code == 404


def test_stamp_workspace_only_fills_empty(monkeypatch) -> None:
    from app.models import Draft
    from app.web_api import _stamp_workspace

    empty = SimpleNamespace(workspace_id=None)
    already = SimpleNamespace(workspace_id="default")

    def fake_scope_for(row):
        class FakeSession:
            def get(self, model, obj_id):
                del model, obj_id
                return row

        @contextmanager
        def scope():
            yield FakeSession()

        return scope

    monkeypatch.setattr("app.web_api.session_scope", fake_scope_for(empty))
    _stamp_workspace(Draft, 1, "ws-b")
    assert empty.workspace_id == "ws-b"

    monkeypatch.setattr("app.web_api.session_scope", fake_scope_for(already))
    _stamp_workspace(Draft, 1, "ws-b")
    assert already.workspace_id == "default"  # never overwrites

    # No-op for the legacy/no-auth path (workspace_id is None).
    _stamp_workspace(Draft, 1, None)


def test_resolve_service_bootstraps_first_owner(monkeypatch) -> None:
    added: dict = {}

    class FakeRepo:
        def __init__(self, session):
            del session

        def get_active_member_by_email(self, email):
            del email
            return None

        def has_any_member(self, workspace_id):
            del workspace_id
            return False  # empty workspace -> first caller becomes owner

        def add_member(self, **kwargs):
            added.update(kwargs)
            return SimpleNamespace(
                id=1,
                workspace_id=kwargs["workspace_id"],
                email=kwargs["email"],
                role=kwargs["role"],
                status=kwargs["status"],
            )

    @contextmanager
    def fake_session_scope():
        yield SimpleNamespace()

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository", FakeRepo
    )
    monkeypatch.setattr(
        "app.services.workspace_service.session_scope", fake_session_scope
    )

    membership = WorkspaceService().resolve("founder@example.com")
    assert membership is not None
    assert membership.role == "owner"
    assert added["role"] == "owner"
    assert added["email"] == "founder@example.com"
