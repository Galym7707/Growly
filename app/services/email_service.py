"""Optional transactional email.

Sending is best-effort and entirely opt-in: with no SMTP settings configured
the service is a no-op and the caller falls back to copyable invite links.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return self.settings.smtp_configured()

    def invite_url(self, invite_path: str) -> str | None:
        base = (self.settings.app_base_url or "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}{invite_path}"

    def send_invitation(
        self,
        *,
        to_email: str,
        invite_url: str,
        role_label: str,
    ) -> bool:
        """Send an invite email. Returns True only if it was actually sent."""
        if not self.is_configured():
            return False
        message = EmailMessage()
        message["Subject"] = "Приглашение в Growly"
        message["From"] = self.settings.smtp_from or ""
        message["To"] = to_email
        message.set_content(
            "Вас пригласили в рабочее пространство Growly "
            f"(роль: {role_label}).\n\n"
            f"Откройте ссылку, чтобы принять приглашение:\n{invite_url}\n\n"
            "Если вы не ожидали это письмо, просто проигнорируйте его."
        )
        try:
            self._deliver(message)
            return True
        except Exception as exc:  # noqa: BLE001 - email is best-effort
            logger.warning("Could not send invitation email: %s", type(exc).__name__)
            return False

    def _deliver(self, message: EmailMessage) -> None:
        host = self.settings.smtp_host or ""
        port = self.settings.smtp_port
        user = self.settings.smtp_user
        password = self.settings.smtp_password_value()
        timeout = 15
        if self.settings.smtp_use_tls:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(message)
