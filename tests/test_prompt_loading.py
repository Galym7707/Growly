from __future__ import annotations

import pytest

from app.services.groq_service import load_prompt


@pytest.mark.parametrize(
    "prompt_name",
    [
        "competitor_report.md",
        "content_plan.md",
        "market_search_analysis.md",
        "market_scan_report.md",
        "content_plan_source_batch.md",
        "source_discovery.md",
        "source_monitoring.md",
        "asset_post.md",
        "brief_analysis.md",
        "case_post.md",
        "pain_point_post.md",
        "educational_post.md",
        "comparison_post.md",
        "weekly_digest.md",
        "reels_shorts_script.md",
        "whatsapp_template.md",
        "draft_from_plan.md",
        "review_analysis.md",
        "reels_script.md",
        "whatsapp_message.md",
        "weekly_performance_report.md",
    ],
)
def test_required_prompt_can_be_loaded(prompt_name: str) -> None:
    prompt = load_prompt(prompt_name)
    assert "{context_json}" in prompt
    assert len(prompt) > 100


def test_prompt_loader_blocks_path_traversal() -> None:
    with pytest.raises(FileNotFoundError):
        load_prompt("../.env")
