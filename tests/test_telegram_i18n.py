from __future__ import annotations

from app.bot.i18n import normalize_language, set_current_language, tr
from app.bot.keyboards import (
    language_keyboard,
    main_menu_keyboard,
    settings_menu_keyboard,
)


def labels(markup: object) -> list[list[str]]:
    return [
        [button.text for button in row]
        for row in markup.keyboard  # type: ignore[attr-defined]
    ]


def test_language_normalization_supports_three_locales() -> None:
    assert normalize_language("ru-RU") == "ru"
    assert normalize_language("en_US") == "en"
    assert normalize_language("kk-KZ") == "kk"
    assert normalize_language("de") == "ru"


def test_keyboards_follow_current_language() -> None:
    try:
        set_current_language("en")
        assert labels(main_menu_keyboard())[0] == [
            "Market analysis",
            "Content plan",
        ]
        assert ["Language"] in labels(settings_menu_keyboard())

        set_current_language("kk")
        assert labels(main_menu_keyboard())[0] == [
            "Нарықты талдау",
            "Контент-жоспар",
        ]
        assert ["Тіл"] in labels(settings_menu_keyboard())
    finally:
        set_current_language("ru")


def test_language_keyboard_has_stable_callback_values() -> None:
    callbacks = [
        button.callback_data
        for row in language_keyboard().inline_keyboard
        for button in row
    ]
    assert callbacks == ["language:ru", "language:en", "language:kk"]


def test_translation_interpolates_values() -> None:
    assert tr("Подтвердить #{id}", "en", id=12) == "Approve #12"
