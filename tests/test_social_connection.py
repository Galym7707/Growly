from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import get_settings
from app.main import app
from app.services.social_connection_service import SocialConnectionService


def _open_api(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "growly_web_api_key", None)


def test_smtp_app_password_ignores_display_spaces(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_password", SecretStr("wmtt ispb clbi mwzd"))

    assert settings.smtp_password_value() == "wmttispbclbimwzd"


# -- admin gating -------------------------------------------------------------


def test_admin_endpoint_denies_non_admin(monkeypatch) -> None:
    _open_api(monkeypatch)
    monkeypatch.setattr(get_settings(), "admin_emails", "owner@growly.app")
    monkeypatch.setattr(get_settings(), "admin_secret", None)
    response = TestClient(app).get(
        "/api/admin/blotato/status",
        headers={"X-Growly-User-Email": "random@user.com"},
    )
    assert response.status_code == 403


def test_admin_endpoint_allows_admin_email(monkeypatch) -> None:
    _open_api(monkeypatch)
    monkeypatch.setattr(get_settings(), "admin_emails", "owner@growly.app")

    async def fake_status(self) -> dict:
        return {"api_key_configured": False, "connected": False, "accounts_count": 0}

    monkeypatch.setattr(
        "app.web_api.SocialConnectionService.admin_blotato_status", fake_status
    )
    response = TestClient(app).get(
        "/api/admin/blotato/status",
        headers={"X-Growly-User-Email": "owner@growly.app"},
    )
    assert response.status_code == 200
    assert response.json()["api_key_configured"] is False


def test_admin_endpoint_denied_when_no_admins_configured(monkeypatch) -> None:
    _open_api(monkeypatch)
    monkeypatch.setattr(get_settings(), "admin_emails", "")
    monkeypatch.setattr(get_settings(), "admin_secret", None)
    response = TestClient(app).get("/api/admin/blotato/status")
    assert response.status_code == 403


# -- status state machine -----------------------------------------------------


def _patch_repo(monkeypatch, *, account=None, request=None) -> None:
    @contextmanager
    def fake_scope():
        yield SimpleNamespace()

    monkeypatch.setattr(
        "app.services.social_connection_service.session_scope", fake_scope
    )
    monkeypatch.setattr(
        "app.services.social_connection_service.IntegrationsRepository",
        lambda session: SimpleNamespace(
            connected_account=lambda w, p: account,
            latest_request=lambda w, p: request,
        ),
    )


@pytest.mark.asyncio
async def test_create_request_notifies_admins(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_emails", "owner@growly.app")
    monkeypatch.setattr(settings, "app_base_url", "https://growly.example")
    created_request = SimpleNamespace(
        id=9,
        workspace_id="ws-1",
        user_email="user@example.com",
        platform="instagram",
        requested_username="@brand",
        status="pending",
        admin_note=None,
        user_note=None,
        created_at=None,
        resolved_at=None,
    )

    @contextmanager
    def fake_scope():
        yield SimpleNamespace()

    monkeypatch.setattr(
        "app.services.social_connection_service.session_scope", fake_scope
    )

    state = {"request": None}

    class FakeRepo:
        def __init__(self, session) -> None:
            pass

        def connected_account(self, workspace, platform):
            return None

        def latest_request(self, workspace, platform):
            return state["request"]

        def create_request(self, **kwargs):
            state["request"] = created_request
            return created_request

    sent: list[dict] = []

    class FakeEmail:
        def send_social_connection_request(self, **kwargs):
            sent.append(kwargs)
            return True

    monkeypatch.setattr(
        "app.services.social_connection_service.IntegrationsRepository",
        FakeRepo,
    )
    service = SocialConnectionService(settings=settings, email_service=FakeEmail())
    result = await service.create_request(
        "ws-1", "user@example.com", "instagram", "@brand"
    )

    assert result["state"] == "pending"
    assert sent == [
        {
            "to_email": "owner@growly.app",
            "platform": "instagram",
            "workspace_id": "ws-1",
            "user_email": "user@example.com",
            "requested_username": "@brand",
            "admin_url": "https://growly.example/admin/integrations/blotato",
        }
    ]


@pytest.mark.asyncio
async def test_status_not_connected(monkeypatch) -> None:
    _patch_repo(monkeypatch, account=None, request=None)
    result = await SocialConnectionService().status("ws-1", "instagram")
    assert result["state"] == "not_connected"
    assert result["account"] is None


@pytest.mark.asyncio
async def test_status_pending(monkeypatch) -> None:
    request = SimpleNamespace(
        id=5,
        workspace_id="ws-1",
        user_email="u@x.com",
        platform="instagram",
        requested_username="@brand",
        status="pending",
        admin_note=None,
        user_note=None,
        created_at=None,
        resolved_at=None,
    )
    _patch_repo(monkeypatch, account=None, request=request)
    result = await SocialConnectionService().status("ws-1", "instagram")
    assert result["state"] == "pending"
    assert result["request"]["requested_username"] == "@brand"


@pytest.mark.asyncio
async def test_status_connected(monkeypatch) -> None:
    account = SimpleNamespace(
        platform="instagram",
        provider="blotato",
        external_account_id="acc-1",
        username="@brand",
        display_name="Brand",
        status="connected",
        connected_at=None,
        last_checked_at=None,
    )
    _patch_repo(monkeypatch, account=account, request=None)
    result = await SocialConnectionService().status("ws-1", "instagram")
    assert result["state"] == "connected"
    assert result["account"]["external_account_id"] == "acc-1"
    # No secret/raw key must leak into the payload.
    assert "api_key" not in str(result).lower()
