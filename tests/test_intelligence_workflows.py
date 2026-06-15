from app.services.content_plan_service import ContentPlanService
from app.services.source_analysis_service import SourceAnalysisService


def test_source_import_split_supports_blank_lines_and_delimiters() -> None:
    items = SourceAnalysisService.split_import_text(
        "First competitor post\n\nSecond item\n---\nThird item"
    )
    assert items == ["First competitor post", "Second item", "Third item"]


STRICT_MIX = {
    "min_posts": 5,
    "min_videos": 2,
    "require_whatsapp": True,
    "require_digest": True,
}


def test_content_plan_mix_requires_posts_video_whatsapp_and_digest() -> None:
    items = [
        {"channel": "Telegram", "content_type": "post"} for _ in range(5)
    ] + [
        {"channel": "Instagram", "content_type": "Reels"},
        {"channel": "Instagram", "content_type": "short video"},
        {"channel": "WhatsApp", "content_type": "message"},
        {"channel": "Telegram", "content_type": "weekly digest"},
    ]
    ContentPlanService._validate_mix(items, STRICT_MIX)


def test_content_plan_mix_rejects_missing_digest() -> None:
    items = [
        {"channel": "Telegram", "content_type": "post"} for _ in range(6)
    ] + [
        {"channel": "Instagram", "content_type": "Reels"},
        {"channel": "Instagram", "content_type": "video"},
        {"channel": "WhatsApp", "content_type": "message"},
    ]
    try:
        ContentPlanService._validate_mix(items, STRICT_MIX)
    except Exception as exc:
        assert "weekly digest" in str(exc)
    else:
        raise AssertionError("A content plan without a digest must be rejected.")


def test_content_plan_mix_accepts_russian_content_type_names() -> None:
    items = [
        {"channel": "Telegram", "content_type": "образовательный пост"}
        for _ in range(5)
    ] + [
        {"channel": "Instagram", "content_type": "короткое видео"},
        {"channel": "Instagram", "content_type": "ролик"},
        {"channel": "WhatsApp", "content_type": "сообщение"},
        {"channel": "Telegram", "content_type": "недельный дайджест"},
    ]
    ContentPlanService._validate_mix(items, STRICT_MIX)
