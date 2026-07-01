from __future__ import annotations

from app.config import Settings
from app.services.replicate_service import ReplicateService


def _service(**env: str) -> ReplicateService:
    settings = Settings(
        DATABASE_URL="postgresql://u:p@localhost/db",
        REPLICATE_ENABLED=env.get("enabled", "true"),
        REPLICATE_API_TOKEN=env.get("token", "r8_test"),
        REPLICATE_VIDEO_MODEL=env.get("model", "minimax/video-01"),
    )
    return ReplicateService(settings)


def test_enabled_requires_flag_and_token() -> None:
    assert _service().is_enabled() is True
    assert _service(token="").is_enabled() is False
    assert _service(enabled="false").is_enabled() is False


def test_normalize_maps_status_and_extracts_urls() -> None:
    service = _service()
    done = service._normalize(
        {"id": "abc", "status": "succeeded", "output": ["https://x/v.mp4"]}
    )
    assert done == {
        "id": "abc",
        "status": "done",
        "media_urls": ["https://x/v.mp4"],
        "error": None,
    }

    processing = service._normalize({"id": "abc", "status": "processing"})
    assert processing["status"] == "generating-media"
    assert processing["media_urls"] == []

    failed = service._normalize(
        {"id": "abc", "status": "failed", "error": "boom"}
    )
    assert failed["status"] == "failed"
    assert failed["error"] == "boom"


def test_normalize_supports_string_and_dict_output() -> None:
    service = _service()
    assert service._normalize(
        {"id": "a", "status": "succeeded", "output": "https://x/one.mp4"}
    )["media_urls"] == ["https://x/one.mp4"]
    assert service._normalize(
        {"id": "a", "status": "succeeded", "output": {"video": "https://x/d.mp4"}}
    )["media_urls"] == ["https://x/d.mp4"]


def test_model_selection_by_kind() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://u:p@localhost/db",
        REPLICATE_VIDEO_MODEL="minimax/video-01",
        REPLICATE_IMAGE_MODEL="black-forest-labs/flux-schnell",
    )
    assert settings.replicate_model("video") == "minimax/video-01"
    assert settings.replicate_model("image") == "black-forest-labs/flux-schnell"
    assert settings.replicate_model("audio") is None
