from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.bitrix_webhook import verify_secret


def test_verify_secret_accepts_matching_token() -> None:
    settings = SimpleNamespace(
        bitrix_enabled=True,
        bitrix_webhook_secret=SimpleNamespace(get_secret_value=lambda: "s3cret"),
    )
    verify_secret("s3cret", settings)


def test_verify_secret_rejects_bad_token() -> None:
    settings = SimpleNamespace(
        bitrix_enabled=True,
        bitrix_webhook_secret=SimpleNamespace(get_secret_value=lambda: "s3cret"),
    )
    with pytest.raises(HTTPException):
        verify_secret("wrong", settings)


def test_verify_secret_rejects_when_disabled() -> None:
    settings = SimpleNamespace(bitrix_enabled=False, bitrix_webhook_secret=None)
    with pytest.raises(HTTPException):
        verify_secret("anything", settings)
