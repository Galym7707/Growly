from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import get_settings
from app.main import app
from app.services.blotato_service import BlotatoService
from app.services.social_publishing_service import SocialPublishingService
from app.utils.errors import BlotatoServiceError, ConfigurationError


def _enable_blotato(monkeypatch, key: str = "test-secret-key") -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "blotato_enabled", True)
    monkeypatch.setattr(settings, "blotato_api_key", SecretStr(key))


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = b"{}" if payload is not None else (text.encode() or b"")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeClient:
    captured: dict = {}
    response = FakeResponse(payload={})

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method, url, headers=None, json=None):
        FakeClient.captured = {
            "method": method,
            "url": url,
            "headers": headers or {},
            "json": json,
        }
        return FakeClient.response


# -- configuration / friendly errors -----------------------------------------


def test_blotato_disabled_returns_friendly_error(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "blotato_enabled", False)
    service = BlotatoService(settings)
    assert service.is_enabled() is False
    with pytest.raises(BlotatoServiceError) as exc:
        service._require_enabled()
    assert "Blotato не подключён" in str(exc.value)


def test_blotato_missing_api_key_returns_configuration_error(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "blotato_enabled", True)
    monkeypatch.setattr(settings, "blotato_api_key", None)
    service = BlotatoService(settings)
    assert service.is_enabled() is False
    with pytest.raises(ConfigurationError):
        service._require_enabled()


# -- provider calls -----------------------------------------------------------


@pytest.mark.asyncio
async def test_list_accounts_calls_provider_with_header(monkeypatch) -> None:
    _enable_blotato(monkeypatch, key="abc123")
    FakeClient.response = FakeResponse(
        payload={
            "accounts": [
                {"id": "1", "platform": "instagram", "username": "@brand", "displayName": "Brand IG"},
                {"id": "2", "platform": "threads", "username": "@brand", "status": "connected"},
            ]
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    accounts = await BlotatoService(get_settings()).list_accounts()

    assert FakeClient.captured["method"] == "GET"
    assert FakeClient.captured["url"].endswith("/users/me/accounts")
    assert FakeClient.captured["headers"].get("blotato-api-key") == "abc123"
    assert accounts[0]["platform"] == "instagram"
    assert accounts[0]["display_name"] == "Brand IG"
    assert accounts[1]["platform"] == "threads"


@pytest.mark.asyncio
async def test_publish_post_builds_blotato_body(monkeypatch) -> None:
    _enable_blotato(monkeypatch)
    captured: dict = {}

    async def fake_request(self, method, path, *, json=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"submissionId": "sub-1", "status": "submitted", "url": "https://x/p"}

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    service = BlotatoService(get_settings())

    result = await service.publish_post(
        platform="x", account_id="acc-1", text="hello", media_urls=["u1"]
    )

    assert captured["path"] == "/posts"
    assert captured["json"]["post"]["accountId"] == "acc-1"
    assert captured["json"]["post"]["target"]["targetType"] == "twitter"
    assert captured["json"]["post"]["content"]["text"] == "hello"
    assert captured["json"]["post"]["content"]["platform"] == "twitter"
    assert result["post_submission_id"] == "sub-1"
    assert result["url"] == "https://x/p"


@pytest.mark.asyncio
async def test_threads_payload_matches_provider_contract(monkeypatch) -> None:
    _enable_blotato(monkeypatch)
    captured: dict = {}

    async def fake_request(self, method, path, *, json=None):
        captured["json"] = json
        return {"submissionId": "threads-1", "status": "submitted"}

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    await BlotatoService(get_settings()).publish_post(
        platform="threads", account_id="7520", text="hello", media_urls=[]
    )

    post = captured["json"]["post"]
    assert post["content"]["platform"] == "threads"
    assert post["target"]["targetType"] == "threads"


@pytest.mark.asyncio
async def test_create_media_upload_returns_presigned_and_public_urls(monkeypatch) -> None:
    _enable_blotato(monkeypatch)
    captured: dict = {}

    async def fake_request(self, method, path, *, json=None):
        captured.update({"method": method, "path": path, "json": json})
        return {
            "presignedUrl": "https://upload.example/signed",
            "publicUrl": "https://cdn.example/photo.jpg",
        }

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    result = await BlotatoService(get_settings()).create_media_upload("photo.jpg")

    assert captured == {
        "method": "POST",
        "path": "/media/uploads",
        "json": {"filename": "photo.jpg"},
    }
    assert result["public_url"] == "https://cdn.example/photo.jpg"


@pytest.mark.asyncio
async def test_create_visual_uses_supported_template(monkeypatch) -> None:
    _enable_blotato(monkeypatch)
    calls: list[dict] = []

    async def fake_request(self, method, path, *, json=None):
        calls.append({"method": method, "path": path, "json": json})
        if path == "/videos/templates":
            # Default id is present in the account, so it should be used as-is.
            return {"items": [{"id": "5903fe43-514d-40ee-a060-0d6628c5f8fd"}]}
        return {"item": {"id": "visual-1", "status": "queueing"}}

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    result = await BlotatoService(get_settings()).create_visual(
        kind="video", prompt="Create a short product video", title="Post visual"
    )

    create = calls[-1]
    assert create["path"] == "/videos/from-templates"
    assert create["json"]["templateId"] == "5903fe43-514d-40ee-a060-0d6628c5f8fd"
    assert create["json"]["render"] is True
    assert result == {"id": "visual-1", "status": "queueing", "media_urls": []}


@pytest.mark.asyncio
async def test_create_visual_resolves_rotated_template(monkeypatch) -> None:
    """When the default id is gone, match a live template by its title."""

    _enable_blotato(monkeypatch)
    calls: list[dict] = []

    async def fake_request(self, method, path, *, json=None):
        calls.append({"method": method, "path": path, "json": json})
        if path == "/videos/templates":
            return {
                "items": [
                    {"id": "new-carousel", "title": "Instagram Carousel Slideshow"},
                    {"id": "new-voice", "title": "AI Video with AI Voice"},
                ]
            }
        return {"item": {"id": "visual-9", "status": "queueing"}}

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    result = await BlotatoService(get_settings()).create_visual(
        kind="video", prompt="Create a short product video"
    )

    create = calls[-1]
    assert create["path"] == "/videos/from-templates"
    assert create["json"]["templateId"] == "new-voice"
    assert result["id"] == "visual-9"


@pytest.mark.asyncio
async def test_create_visual_falls_back_when_templates_unavailable(monkeypatch) -> None:
    """A failing templates listing must not block generation."""

    _enable_blotato(monkeypatch)
    calls: list[dict] = []

    async def fake_request(self, method, path, *, json=None):
        calls.append({"method": method, "path": path, "json": json})
        if path == "/videos/templates":
            raise BlotatoServiceError("Не удалось отправить публикацию.")
        return {"item": {"id": "visual-1", "status": "queueing"}}

    monkeypatch.setattr(BlotatoService, "_request", fake_request)
    result = await BlotatoService(get_settings()).create_visual(
        kind="image", prompt="Create a carousel"
    )

    create = calls[-1]
    assert create["path"] == "/videos/from-templates"
    assert create["json"]["templateId"] == "53cfec04-2500-41cf-8cc1-ba670d2c341a"
    assert result["status"] == "queueing"


def test_visual_status_normalizes_generated_media() -> None:
    result = BlotatoService._normalize_visual(
        {
            "item": {
                "id": "visual-1",
                "status": "done",
                "mediaUrl": "https://cdn.example/video.mp4",
                "imageUrls": ["https://cdn.example/slide.jpg"],
            }
        }
    )
    assert result["status"] == "done"
    assert result["media_urls"] == [
        "https://cdn.example/slide.jpg",
        "https://cdn.example/video.mp4",
    ]


def test_map_platform_to_account_uses_env_fallback(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "blotato_instagram_account_id", "env-ig")

    @contextmanager
    def fake_scope():
        yield SimpleNamespace()

    monkeypatch.setattr("app.services.blotato_service.session_scope", fake_scope)
    monkeypatch.setattr(
        "app.services.blotato_service.IntegrationsRepository",
        lambda session: SimpleNamespace(get_target=lambda w, p: None),
    )

    mapping = BlotatoService(settings).map_platform_to_account("default", "instagram")
    assert mapping == {"account_id": "env-ig", "page_id": None}


# -- publishing orchestration -------------------------------------------------


def _publish_service(
    monkeypatch,
    *,
    mapping,
    publish_result=None,
    raises=None,
    draft_workspace=None,
):
    _enable_blotato(monkeypatch)
    recorded: list[dict] = []
    service = SocialPublishingService()

    monkeypatch.setattr(
        service,
        "_load_draft",
        staticmethod(
            lambda draft_id: SimpleNamespace(
                draft_text="Post body",
                status="approved",
                workspace_id=draft_workspace,
            )
        ),
    )
    monkeypatch.setattr(service.blotato, "is_enabled", lambda: True)
    monkeypatch.setattr(service.blotato, "validate_platform", lambda p: True)
    monkeypatch.setattr(service, "_resolve_account", lambda w, p: mapping)

    async def fake_publish(**kwargs):
        if raises is not None:
            raise raises
        return publish_result

    monkeypatch.setattr(service.blotato, "publish_post", fake_publish)

    def fake_record(workspace, draft_id, platform, account_id, page_id, status, scheduled_time, submission_id, url, error_message):
        recorded.append(
            {
                "workspace": workspace,
                "platform": platform,
                "status": status,
                "scheduled_time": scheduled_time,
                "submission_id": submission_id,
                "error_message": error_message,
            }
        )
        return len(recorded)

    monkeypatch.setattr(service, "_record_publication", staticmethod(fake_record))
    monkeypatch.setattr(service, "_mark_draft_published", staticmethod(lambda draft_id: None))
    return service, recorded


@pytest.mark.asyncio
async def test_publish_draft_creates_publication_record(monkeypatch) -> None:
    service, recorded = _publish_service(
        monkeypatch,
        mapping={"account_id": "acc-1", "page_id": None},
        publish_result={"post_submission_id": "sub-1", "status": "submitted", "url": "https://x/p"},
    )
    result = await service.publish_draft(
        workspace_id="default",
        draft_id=7,
        platforms=["instagram"],
        publish_now=True,
        scheduled_time=None,
        media_urls=[],
        language="ru",
    )
    assert result["publication_ids"] == [1]
    assert result["blotato_submissions"][0]["post_submission_id"] == "sub-1"
    assert recorded[0]["status"] == "submitted"


@pytest.mark.asyncio
async def test_publish_draft_rejects_other_workspace(monkeypatch) -> None:
    service = SocialPublishingService()
    monkeypatch.setattr(
        service,
        "_load_draft",
        staticmethod(
            lambda draft_id: SimpleNamespace(
                draft_text="Post body",
                status="approved",
                workspace_id="workspace-a",
            )
        ),
    )

    with pytest.raises(ValueError, match="Черновик"):
        await service.publish_draft(
            workspace_id="workspace-b",
            draft_id=7,
            platforms=["threads"],
            publish_now=True,
            scheduled_time=None,
            media_urls=[],
            language="ru",
        )


@pytest.mark.asyncio
async def test_schedule_draft_creates_scheduled_publication(monkeypatch) -> None:
    service, recorded = _publish_service(
        monkeypatch,
        mapping={"account_id": "acc-1", "page_id": None},
        publish_result={"post_submission_id": "sub-2", "status": "scheduled", "url": None},
    )
    result = await service.publish_draft(
        workspace_id="default",
        draft_id=7,
        platforms=["threads"],
        publish_now=False,
        scheduled_time="2026-06-21T10:00:00+05:00",
        media_urls=[],
        language="ru",
    )
    assert recorded[0]["status"] == "scheduled"
    assert recorded[0]["scheduled_time"] == "2026-06-21T10:00:00+05:00"
    assert result["blotato_submissions"][0]["status"] == "scheduled"


@pytest.mark.asyncio
async def test_provider_error_is_saved_safely(monkeypatch) -> None:
    service, recorded = _publish_service(
        monkeypatch,
        mapping={"account_id": "acc-1", "page_id": None},
        raises=BlotatoServiceError("Не удалось отправить публикацию.", status=500, provider_message="boom"),
    )
    marked_published: list[int] = []
    monkeypatch.setattr(
        service,
        "_mark_draft_published",
        lambda draft_id: marked_published.append(draft_id),
    )
    result = await service.publish_draft(
        workspace_id="default",
        draft_id=7,
        platforms=["instagram"],
        publish_now=True,
        scheduled_time=None,
        media_urls=[],
        language="ru",
    )
    assert result["blotato_submissions"][0]["status"] == "failed"
    assert recorded[0]["status"] == "failed"
    assert "Blotato: boom" in result["blotato_submissions"][0]["error"]
    assert marked_published == []
    # The recorded error message must not contain the API key.
    assert "test-secret-key" not in str(recorded[0]["error_message"])


@pytest.mark.asyncio
async def test_workspace_without_mapping_cannot_publish(monkeypatch) -> None:
    service, recorded = _publish_service(
        monkeypatch,
        mapping=None,  # workspace has no account mapping and no env fallback
        draft_workspace="other-workspace",
    )
    result = await service.publish_draft(
        workspace_id="other-workspace",
        draft_id=7,
        platforms=["instagram"],
        publish_now=True,
        scheduled_time=None,
        media_urls=[],
        language="ru",
    )
    assert result["blotato_submissions"][0]["status"] == "failed"
    assert "не подключён" in result["blotato_submissions"][0]["error"].lower()
    assert recorded[0]["status"] == "failed"


def test_api_key_is_not_exposed_in_errors() -> None:
    error = BlotatoServiceError(
        "Не удалось отправить публикацию.", status=401, provider_message="unauthorized"
    )
    details = error.safe_details()
    assert "provider_message" in details
    assert "secret" not in str(details).lower()


# -- API endpoints ------------------------------------------------------------


def test_integrations_status_endpoint(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    async def fake_status(self, workspace_id):
        return {
            "telegram": {"connected": True},
            "notion": {"connected": True},
            "blotato": {"enabled": True, "connected": True, "accounts_count": 2},
        }

    monkeypatch.setattr(
        "app.web_api.SocialPublishingService.integrations_status", fake_status
    )
    response = TestClient(app).get("/api/integrations/status")
    assert response.status_code == 200
    body = response.json()
    assert body["blotato"]["accounts_count"] == 2
    assert "api_key" not in str(body).lower()


def test_blotato_accounts_endpoint(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)

    async def fake_list(self, workspace_id):
        return [{"id": "1", "platform": "instagram", "name": "@b", "display_name": "B", "connected": True}]

    monkeypatch.setattr(
        "app.web_api.SocialPublishingService.list_accounts", fake_list
    )
    response = TestClient(app).get("/api/integrations/blotato/accounts")
    assert response.status_code == 200
    assert response.json()["accounts"][0]["platform"] == "instagram"


def test_publish_endpoint_passes_workspace_from_header(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "growly_web_api_key", None)
    captured: dict = {}

    async def fake_publish(self, **kwargs):
        captured.update(kwargs)
        return {"status": "submitted", "publication_ids": [1], "blotato_submissions": []}

    monkeypatch.setattr(
        "app.web_api.SocialPublishingService.publish_draft", fake_publish
    )
    response = TestClient(app).post(
        "/api/drafts/7/publish-blotato",
        json={"platforms": ["instagram"], "publish_now": True},
        headers={"X-Growly-Workspace-Id": "ws-42"},
    )
    assert response.status_code == 200
    assert captured["workspace_id"] == "ws-42"
    assert captured["draft_id"] == 7
    assert captured["platforms"] == ["instagram"]
