from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.errors import ConfigurationError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Growly", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    default_language: str = Field(default="ru", alias="DEFAULT_LANGUAGE")

    telegram_bot_api_key: SecretStr | None = Field(
        default=None, alias="TELEGRAM_BOT_API_KEY"
    )
    telegram_publish_chat_id: str | None = Field(
        default=None, alias="TELEGRAM_PUBLISH_CHAT_ID"
    )
    telegram_channel_id: str | None = Field(default=None, alias="TELEGRAM_CHANNEL_ID")

    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="GROQ_MODEL",
    )
    github_models_token: SecretStr | None = Field(
        default=None,
        alias="GITHUB_MODELS_TOKEN",
    )
    github_models_base_url: str = Field(
        default="https://models.github.ai/inference",
        alias="GITHUB_MODELS_BASE_URL",
    )
    github_models_model: str = Field(
        default="openai/gpt-5-mini",
        alias="GITHUB_MODELS_MODEL",
    )
    ai_primary_provider: str = Field(
        default="github_models",
        alias="AI_PRIMARY_PROVIDER",
    )
    ai_fallback_provider: str = Field(
        default="groq",
        alias="AI_FALLBACK_PROVIDER",
    )

    search_provider: str | None = Field(default=None, alias="SEARCH_PROVIDER")
    tavily_api_key: SecretStr | None = Field(default=None, alias="TAVILY_API_KEY")
    search_max_results: int = Field(default=10, ge=1, le=20, alias="SEARCH_MAX_RESULTS")
    search_depth: str = Field(default="basic", alias="SEARCH_DEPTH")
    search_save_raw: bool = Field(default=True, alias="SEARCH_SAVE_RAW")

    supabase_url: SecretStr | None = Field(default=None, alias="SUPABASE_URL")
    supabase_publishable_api_key: SecretStr | None = Field(
        default=None, alias="SUPABASE_PUBLISHABLE_API_KEY"
    )
    supabase_secret_api_key: SecretStr | None = Field(
        default=None, alias="SUPABASE_SECRET_API_KEY"
    )
    supabase_db_password: SecretStr | None = Field(
        default=None, alias="SUPABASE_DB_PASSWORD"
    )
    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")

    notion_api_key: SecretStr | None = Field(default=None, alias="NOTION_API_KEY")
    notion_root_page_id: str | None = Field(default=None, alias="NOTION_ROOT_PAGE_ID")

    growly_web_api_key: SecretStr | None = Field(
        default=None, alias="GROWLY_WEB_API_KEY"
    )
    web_allowed_origins: str = Field(
        default="http://localhost:3000",
        alias="WEB_ALLOWED_ORIGINS",
    )

    instagram_enabled: bool = Field(default=False, alias="INSTAGRAM_ENABLED")
    bitrix_enabled: bool = Field(default=False, alias="BITRIX_ENABLED")
    erpnext_enabled: bool = Field(default=False, alias="ERPNEXT_ENABLED")
    crm_provider: str = Field(default="none", alias="CRM_PROVIDER")

    scheduler_enabled: bool = Field(default=False, alias="SCHEDULER_ENABLED")
    weekly_report_day: str = Field(default="monday", alias="WEEKLY_REPORT_DAY")
    weekly_report_hour: int = Field(default=9, ge=0, le=23, alias="WEEKLY_REPORT_HOUR")
    weekly_report_minute: int = Field(
        default=0, ge=0, le=59, alias="WEEKLY_REPORT_MINUTE"
    )
    timezone: str = Field(default="Asia/Almaty", alias="TIMEZONE")

    def require_secret(self, field_name: str, env_name: str) -> str:
        value = getattr(self, field_name)
        if value is None or not value.get_secret_value().strip():
            raise ConfigurationError(f"Required environment variable {env_name} is missing.")
        return value.get_secret_value()

    def require_text(self, field_name: str, env_name: str) -> str:
        value = getattr(self, field_name)
        if value is None or not str(value).strip():
            raise ConfigurationError(f"Required environment variable {env_name} is missing.")
        return str(value).strip()

    def database_dsn(self) -> str:
        return self.require_secret("database_url", "DATABASE_URL")

    def telegram_token(self) -> str:
        return self.require_secret("telegram_bot_api_key", "TELEGRAM_BOT_API_KEY")

    def telegram_publish_target(self) -> str | None:
        preferred = (self.telegram_publish_chat_id or "").strip()
        legacy = (self.telegram_channel_id or "").strip()
        return preferred or legacy or None

    def groq_key(self) -> str:
        return self.require_secret("groq_api_key", "GROQ_API_KEY")

    def github_models_key(self) -> str:
        return self.require_secret(
            "github_models_token",
            "GITHUB_MODELS_TOKEN",
        )

    def ai_model_name(self, provider: str | None = None) -> str:
        provider_name = (provider or self.ai_primary_provider).strip().lower()
        if provider_name == "github_models":
            return self.require_text(
                "github_models_model",
                "GITHUB_MODELS_MODEL",
            )
        if provider_name == "groq":
            return self.require_text("groq_model", "GROQ_MODEL")
        raise ConfigurationError(
            f"Unsupported AI provider {provider_name!r}. "
            "Use 'github_models' or 'groq'."
        )

    def tavily_key(self) -> str:
        return self.require_secret("tavily_api_key", "TAVILY_API_KEY")

    def notion_token(self) -> str:
        return self.require_secret("notion_api_key", "NOTION_API_KEY")

    def allowed_web_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.web_allowed_origins.split(",")
            if origin.strip()
        ]

    def user_language_instruction(self) -> str:
        if self.default_language.strip().lower() == "ru":
            return (
                "Write all user-facing text in Russian. Keep only required "
                "JSON keys, URLs, brand names, and channel names unchanged."
            )
        return (
            f"Write all user-facing text in {self.default_language.strip()}. "
            "Keep only required JSON keys, URLs, brand names, and channel "
            "names unchanged."
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
