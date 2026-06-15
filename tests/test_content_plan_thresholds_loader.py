from app.services.content_plan_service import ContentPlanService


def test_thresholds_default_to_tz_minimums() -> None:
    t = ContentPlanService._thresholds_from_settings({})
    assert t["min_posts"] == 5
    assert t["min_videos"] == 2
    assert t["require_whatsapp"] is False
    assert t["require_digest"] is False


def test_thresholds_read_overrides() -> None:
    raw = {
        "content_plan_min_posts": "7",
        "content_plan_min_videos": "3",
        "content_plan_require_whatsapp": "true",
        "content_plan_require_digest": "1",
    }
    t = ContentPlanService._thresholds_from_settings(raw)
    assert t["min_posts"] == 7
    assert t["min_videos"] == 3
    assert t["require_whatsapp"] is True
    assert t["require_digest"] is True
