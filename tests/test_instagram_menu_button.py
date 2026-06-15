from app.bot.keyboards import create_post_menu_keyboard


def test_create_post_menu_has_instagram_caption() -> None:
    labels = [b.text for row in create_post_menu_keyboard().keyboard for b in row]
    assert "Instagram caption" in labels
