from __future__ import annotations

from datetime import datetime

import pytest

from app.bot.keyboards import approved_keyboard
from app.bot.handlers import parse_schedule_datetime


def test_approved_keyboard_has_schedule_button() -> None:
    markup = approved_keyboard(7, telegram_publish_enabled=True)
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "schedule:7" in callbacks


def test_parse_schedule_datetime_accepts_iso_like() -> None:
    dt = parse_schedule_datetime("2026-07-01 14:30")
    assert isinstance(dt, datetime)
    assert dt.year == 2026 and dt.hour == 14 and dt.minute == 30


def test_parse_schedule_datetime_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_schedule_datetime("not a date")
