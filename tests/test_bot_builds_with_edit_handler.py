from app.bot.bot import build_application
from types import SimpleNamespace


def test_build_application_registers_edit_entry(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.bot.bot.get_settings",
        lambda: SimpleNamespace(
            telegram_token=lambda: "123:abc",
            timezone="Asia/Almaty",
            scheduler_enabled=False,
        ),
    )
    app = build_application()
    patterns = [
        h.entry_points[0].pattern.pattern
        for group in app.handlers.values()
        for h in group
        if hasattr(h, "entry_points") and h.entry_points and hasattr(h.entry_points[0], "pattern") and h.entry_points[0].pattern
    ]
    assert any("edit:" in p for p in patterns)
