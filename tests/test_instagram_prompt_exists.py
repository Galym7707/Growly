from pathlib import Path


def test_instagram_caption_prompt_exists_and_mentions_json() -> None:
    text = Path("app/prompts/instagram_caption.md").read_text(encoding="utf-8")
    assert "draft_text" in text
    assert len(text.strip()) > 50
