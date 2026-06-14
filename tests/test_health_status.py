from __future__ import annotations

import pytest

from app.main import health
from app.runtime_status import telegram_initialized


@pytest.mark.asyncio
async def test_health_exposes_telegram_runtime_status() -> None:
    telegram_initialized.clear()
    payload = await health()
    assert payload["telegram"] == "initializing"

    telegram_initialized.set()
    try:
        payload = await health()
        assert payload["telegram"] == "initialized"
    finally:
        telegram_initialized.clear()
