from __future__ import annotations

import pytest

from app.config import Settings
from app.utils.errors import ConfigurationError


def test_defaults_are_safe() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Growly"
    assert settings.environment == "development"
    assert settings.default_language == "ru"
    assert "Russian" in settings.user_language_instruction()
    assert settings.ai_primary_provider == "github_models"
    assert settings.ai_fallback_provider == "groq"
    assert settings.github_models_base_url == "https://models.github.ai/inference"
    assert settings.github_models_model == "openai/gpt-5-mini"
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert settings.instagram_enabled is False
    assert settings.bitrix_enabled is False
    assert settings.erpnext_enabled is False
    assert settings.scheduler_enabled is False
    assert settings.weekly_report_day == "monday"
    assert settings.weekly_report_hour == 9
    assert settings.weekly_report_minute == 0


def test_missing_required_secret_has_clear_error() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_API_KEY"):
        settings.telegram_token()


def test_secret_value_is_not_in_repr() -> None:
    settings = Settings(
        _env_file=None,
        TELEGRAM_BOT_API_KEY="test-secret-token",
    )
    assert "test-secret-token" not in repr(settings)


def test_publish_chat_id_prefers_new_variable() -> None:
    settings = Settings(
        _env_file=None,
        TELEGRAM_PUBLISH_CHAT_ID="-100111",
        TELEGRAM_CHANNEL_ID="-100222",
    )
    assert settings.telegram_publish_target() == "-100111"


def test_publish_chat_id_falls_back_to_legacy_variable() -> None:
    settings = Settings(
        _env_file=None,
        TELEGRAM_CHANNEL_ID="-100222",
    )
    assert settings.telegram_publish_target() == "-100222"
