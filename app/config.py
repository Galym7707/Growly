from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

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
    publish_to_channel: bool = Field(default=True, alias="PUBLISH_TO_CHANNEL")
    publish_to_group: bool = Field(default=False, alias="PUBLISH_TO_GROUP")

    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        alias="GROQ_MODEL",
    )
    groq_max_concurrent_requests: int = Field(
        default=1, ge=1, le=10, alias="GROQ_MAX_CONCURRENT_REQUESTS"
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
    nvidia_api_key: SecretStr | None = Field(default=None, alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        alias="NVIDIA_BASE_URL",
    )
    nvidia_model: str = Field(
        default="google/gemma-4-31b-it",
        alias="NVIDIA_MODEL",
    )
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        alias="GEMINI_BASE_URL",
    )
    gemini_model: str = Field(
        default="gemini-flash-latest",
        alias="GEMINI_MODEL",
    )
    ai_primary_provider: str = Field(
        default="github_models",
        alias="AI_PRIMARY_PROVIDER",
    )
    ai_fallback_provider: str = Field(
        default="groq",
        alias="AI_FALLBACK_PROVIDER",
    )

    green_api_base_url: str = Field(
        default="https://api.green-api.com",
        alias="GREEN_API_BASE_URL",
    )
    green_api_instance_id: str | None = Field(
        default=None, alias="GREEN_API_INSTANCE_ID"
    )
    green_api_token: SecretStr | None = Field(default=None, alias="GREEN_API_TOKEN")
    whatsapp_group_chat_id: str | None = Field(
        default=None, alias="WHATSAPP_GROUP_CHAT_ID"
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
    database_connect_timeout_seconds: int = Field(
        default=5, ge=2, le=30, alias="DATABASE_CONNECT_TIMEOUT_SECONDS"
    )
    database_pool_timeout_seconds: int = Field(
        default=5, ge=1, le=30, alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )

    notion_api_key: SecretStr | None = Field(default=None, alias="NOTION_API_KEY")
    notion_root_page_id: str | None = Field(default=None, alias="NOTION_ROOT_PAGE_ID")

    growly_web_api_key: SecretStr | None = Field(
        default=None, alias="GROWLY_WEB_API_KEY"
    )
    secrets_encryption_key: SecretStr | None = Field(
        default=None, alias="SECRETS_ENCRYPTION_KEY"
    )
    admin_emails: str = Field(default="", alias="ADMIN_EMAILS")
    admin_secret: SecretStr | None = Field(default=None, alias="ADMIN_SECRET")
    web_allowed_origins: str = Field(
        default="http://localhost:3000",
        alias="WEB_ALLOWED_ORIGINS",
    )

    blotato_enabled: bool = Field(default=False, alias="BLOTATO_ENABLED")
    blotato_api_key: SecretStr | None = Field(default=None, alias="BLOTATO_API_KEY")
    blotato_base_url: str = Field(
        default="https://backend.blotato.com/v2",
        alias="BLOTATO_BASE_URL",
    )
    blotato_instagram_account_id: str | None = Field(
        default=None, alias="BLOTATO_INSTAGRAM_ACCOUNT_ID"
    )
    blotato_threads_account_id: str | None = Field(
        default=None, alias="BLOTATO_THREADS_ACCOUNT_ID"
    )
    blotato_tiktok_account_id: str | None = Field(
        default=None, alias="BLOTATO_TIKTOK_ACCOUNT_ID"
    )
    blotato_youtube_account_id: str | None = Field(
        default=None, alias="BLOTATO_YOUTUBE_ACCOUNT_ID"
    )
    blotato_facebook_account_id: str | None = Field(
        default=None, alias="BLOTATO_FACEBOOK_ACCOUNT_ID"
    )
    blotato_facebook_page_id: str | None = Field(
        default=None, alias="BLOTATO_FACEBOOK_PAGE_ID"
    )
    blotato_linkedin_account_id: str | None = Field(
        default=None, alias="BLOTATO_LINKEDIN_ACCOUNT_ID"
    )
    blotato_linkedin_page_id: str | None = Field(
        default=None, alias="BLOTATO_LINKEDIN_PAGE_ID"
    )
    blotato_x_account_id: str | None = Field(
        default=None, alias="BLOTATO_X_ACCOUNT_ID"
    )

    # Replicate AI-video provider (pay-per-video via credits). Enabled only
    # when both the flag and a token are present.
    replicate_enabled: bool = Field(default=False, alias="REPLICATE_ENABLED")
    replicate_api_token: SecretStr | None = Field(
        default=None, alias="REPLICATE_API_TOKEN"
    )
    replicate_base_url: str = Field(
        default="https://api.replicate.com/v1",
        alias="REPLICATE_BASE_URL",
    )
    replicate_video_model: str = Field(
        default="minimax/video-01", alias="REPLICATE_VIDEO_MODEL"
    )
    replicate_image_model: str | None = Field(
        default=None, alias="REPLICATE_IMAGE_MODEL"
    )
    # How many credits one generated video costs.
    replicate_video_credit_cost: int = Field(
        default=1, ge=1, alias="REPLICATE_VIDEO_CREDIT_COST"
    )

    instagram_enabled: bool = Field(default=False, alias="INSTAGRAM_ENABLED")
    bitrix_enabled: bool = Field(default=False, alias="BITRIX_ENABLED")
    bitrix_webhook_secret: SecretStr | None = Field(
        default=None, alias="BITRIX_WEBHOOK_SECRET"
    )
    bitrix_notify_chat_id: str | None = Field(
        default=None, alias="BITRIX_NOTIFY_CHAT_ID"
    )
    erpnext_enabled: bool = Field(default=False, alias="ERPNEXT_ENABLED")
    crm_provider: str = Field(default="none", alias="CRM_PROVIDER")

    # Optional SMTP for sending team invitations by email. When unset, the app
    # falls back to copyable invite links (no email is sent).
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: SecretStr | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(default=None, alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    # Public base URL of the web app, used to build absolute invite links in
    # emails (e.g. https://growly-five.vercel.app).
    app_base_url: str | None = Field(default=None, alias="APP_BASE_URL")
    # When true (default), an authenticated user with no membership gets a
    # private workspace automatically. Set to false to enforce invite-only
    # access.
    workspace_auto_join: bool = Field(default=True, alias="WORKSPACE_AUTO_JOIN")

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

    def smtp_configured(self) -> bool:
        return bool(
            self.smtp_host
            and self.smtp_host.strip()
            and self.smtp_from
            and self.smtp_from.strip()
        )

    def smtp_password_value(self) -> str | None:
        if self.smtp_password is None:
            return None
        secret = self.smtp_password.get_secret_value().strip()
        normalized = "".join(secret.split())
        return normalized or None

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

    def gemini_key(self) -> str:
        return self.require_secret("gemini_api_key", "GEMINI_API_KEY")

    def nvidia_key(self) -> str:
        return self.require_secret("nvidia_api_key", "NVIDIA_API_KEY")

    def ai_model_name(self, provider: str | None = None) -> str:
        provider_name = (provider or self.ai_primary_provider).strip().lower()
        if provider_name == "github_models":
            return self.require_text(
                "github_models_model",
                "GITHUB_MODELS_MODEL",
            )
        if provider_name == "groq":
            return self.require_text("groq_model", "GROQ_MODEL")
        if provider_name == "gemini":
            return self.require_text("gemini_model", "GEMINI_MODEL")
        if provider_name == "nvidia":
            return self.require_text("nvidia_model", "NVIDIA_MODEL")
        raise ConfigurationError(
            f"Unsupported AI provider {provider_name!r}. "
            "Use 'nvidia', 'gemini', 'groq' or 'github_models'."
        )

    def tavily_key(self) -> str:
        return self.require_secret("tavily_api_key", "TAVILY_API_KEY")

    def notion_token(self) -> str:
        return self.require_secret("notion_api_key", "NOTION_API_KEY")

    def admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    def admin_secret_value(self) -> str | None:
        if self.admin_secret and self.admin_secret.get_secret_value().strip():
            return self.admin_secret.get_secret_value().strip()
        return None

    def blotato_api_key_configured(self) -> bool:
        return bool(
            self.blotato_api_key
            and self.blotato_api_key.get_secret_value().strip()
        )

    def blotato_key(self) -> str:
        return self.require_secret("blotato_api_key", "BLOTATO_API_KEY")

    def blotato_fallback_account(self, platform: str) -> str | None:
        value = getattr(
            self, f"blotato_{platform.strip().lower()}_account_id", None
        )
        return value.strip() if isinstance(value, str) and value.strip() else None

    def blotato_fallback_page(self, platform: str) -> str | None:
        value = getattr(
            self, f"blotato_{platform.strip().lower()}_page_id", None
        )
        return value.strip() if isinstance(value, str) and value.strip() else None

    def replicate_token_configured(self) -> bool:
        return bool(
            self.replicate_api_token
            and self.replicate_api_token.get_secret_value().strip()
        )

    def replicate_is_enabled(self) -> bool:
        return self.replicate_enabled and self.replicate_token_configured()

    def replicate_key(self) -> str:
        return self.require_secret("replicate_api_token", "REPLICATE_API_TOKEN")

    def replicate_model(self, kind: str) -> str | None:
        slug = (kind or "").strip().lower()
        if slug == "video":
            value = (self.replicate_video_model or "").strip()
            return value or None
        if slug == "image":
            value = (self.replicate_image_model or "").strip()
            return value or None
        return None

    def allowed_web_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.web_allowed_origins.split(",")
            if origin.strip()
        ]

    _LANGUAGE_NAMES: ClassVar[dict[str, str]] = {
        "ru": "Russian",
        "en": "English",
        "kk": "Kazakh",
    }

    def user_language_instruction(self, language: str | None = None) -> str:
        """Instruction telling the model which language to answer in.

        When a per-request ``language`` is provided (e.g. the current UI
        locale sent from the web app), it takes precedence over the global
        ``DEFAULT_LANGUAGE`` so the assistant replies in the same language
        as the user instead of always defaulting to Russian.
        """
        raw = (language or self.default_language or "ru").strip()
        name = self._LANGUAGE_NAMES.get(raw.lower(), raw)
        return (
            f"Write all user-facing text in {name}. Keep only required "
            "JSON keys, URLs, brand names, and channel names unchanged."
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
