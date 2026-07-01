class GrowlyError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(GrowlyError):
    """Raised when required configuration is unavailable."""


class WorkspaceAccessError(GrowlyError):
    """Raised when a caller is not allowed to access a workspace resource.

    ``status`` maps to an HTTP status: 403 for permission failures, 404 to hide
    the existence of another workspace's resource.
    """

    def __init__(self, message: str, *, status: int = 403) -> None:
        super().__init__(message)
        self.status = status


class IntegrationError(GrowlyError):
    """Raised when an external integration fails."""


class AIServiceError(IntegrationError):
    """Raised when an AI provider cannot complete a generation request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retry_after: float | None = None,
        provider: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.provider = provider
        self.reason = reason

    @property
    def is_rate_limited(self) -> bool:
        return self.status == 429


class SearchConfigurationError(ConfigurationError):
    """Raised when the configured search provider cannot be initialized."""


class SearchServiceError(IntegrationError):
    """Raised when a web search provider cannot complete a request."""


class BlotatoServiceError(IntegrationError):
    """Raised when the Blotato publishing provider cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        provider_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.provider_message = provider_message

    def safe_details(self) -> dict[str, object]:
        """Provider details safe to surface in development (no secrets)."""

        return {
            "status": self.status,
            "provider_message": self.provider_message or str(self),
        }


class ReplicateServiceError(IntegrationError):
    """Raised when the Replicate AI-video provider cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        provider_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.provider_message = provider_message

    def safe_details(self) -> dict[str, object]:
        """Provider details safe to surface in development (no secrets)."""

        return {
            "status": self.status,
            "provider_message": self.provider_message or str(self),
        }


class InsufficientCreditsError(GrowlyError):
    """Raised when a workspace lacks enough video credits to generate media."""

    status = 402

    def __init__(
        self,
        message: str = "Недостаточно кредитов для генерации видео.",
        *,
        balance: int = 0,
        required: int = 1,
    ) -> None:
        super().__init__(message)
        self.balance = balance
        self.required = required


class NotionServiceError(IntegrationError):
    """Raised when Notion cannot complete a synchronization request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        notion_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.notion_message = notion_message

    def safe_details(self) -> str:
        parts = [
            f"status={self.status if self.status is not None else 'unknown'}",
            f"code={self.code or 'unknown'}",
            f"message={self.notion_message or str(self)}",
        ]
        return " ".join(parts)
