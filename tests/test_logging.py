from app.utils.logging import redact


def test_redacts_telegram_api_url() -> None:
    value = "GET https://api.telegram.org/bot123456789:abcdefghijklmnopqrstuvwxyz/getMe"
    redacted = redact(value)
    assert "123456789:" not in redacted
    assert "bot[REDACTED]/getMe" in redacted


def test_redacts_database_password() -> None:
    value = "postgresql://postgres:private-password@example.test:5432/postgres"
    redacted = redact(value)
    assert "private-password" not in redacted
