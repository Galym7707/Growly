from app.config import Settings


def test_bitrix_webhook_secret_defaults_none() -> None:
    s = Settings(_env_file=None)
    assert s.bitrix_webhook_secret is None
