from app.bot.keyboards import approval_keyboard


def test_approval_keyboard_has_edit_button() -> None:
    markup = approval_keyboard(42)
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "edit:42" in callbacks
    assert "approve:42" in callbacks
    assert "regenerate:42" in callbacks
    assert "reject:42" in callbacks
