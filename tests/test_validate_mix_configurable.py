import pytest

from app.services.content_plan_service import ContentPlanService
from app.utils.errors import AIServiceError


def items(posts: int, videos: int) -> list[dict]:
    out = [{"channel": "Telegram", "content_type": "promo post"} for _ in range(posts)]
    out += [{"channel": "Instagram", "content_type": "reels script"} for _ in range(videos)]
    return out


def test_tz_minimum_passes_with_5_posts_2_videos() -> None:
    thresholds = {"min_posts": 5, "min_videos": 2, "require_whatsapp": False, "require_digest": False}
    ContentPlanService._validate_mix(items(5, 2), thresholds)


def test_below_minimum_raises() -> None:
    thresholds = {"min_posts": 5, "min_videos": 2, "require_whatsapp": False, "require_digest": False}
    with pytest.raises(AIServiceError):
        ContentPlanService._validate_mix(items(3, 1), thresholds)


def test_whatsapp_required_when_configured() -> None:
    thresholds = {"min_posts": 5, "min_videos": 2, "require_whatsapp": True, "require_digest": False}
    with pytest.raises(AIServiceError):
        ContentPlanService._validate_mix(items(5, 2), thresholds)
