"""Unit tests must never load deployment credentials from the checkout's .env."""

from app.config import Settings, get_settings


Settings.model_config = {**Settings.model_config, "env_file": None}
get_settings.cache_clear()
