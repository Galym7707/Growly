"""Workspace / team access control.

This is the single source of truth for *who* may do *what* in a workspace.
Identity is email-based (the Next proxy verifies the Supabase session and
forwards the verified email); membership rows decide access.

Phase-1 bootstrap: the app was single-tenant, so legacy data may still live in
the ``default`` workspace. New authenticated callers are provisioned into their
own workspace instead of being joined to ``default``; otherwise separate emails
can see the same legacy workspace.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.config import Settings, get_settings
from app.database import session_scope
from app.repositories.workspace_repo import WorkspaceRepository
from app.utils.errors import WorkspaceAccessError

DEFAULT_WORKSPACE_ID = "default"

ROLES = ("owner", "admin", "editor", "viewer")

# Roles allowed to perform each capability. Viewer is read-only.
_MANAGE_TEAM_ROLES = frozenset({"owner", "admin"})
_MANAGE_INTEGRATIONS_ROLES = frozenset({"owner", "admin"})
_PUBLISH_ROLES = frozenset({"owner", "admin", "editor"})
_EDIT_ROLES = frozenset({"owner", "admin", "editor"})
_VIEW_ROLES = frozenset(ROLES)


def is_valid_role(role: str) -> bool:
    return role in ROLES


def can_view(role: str) -> bool:
    return role in _VIEW_ROLES


def can_edit(role: str) -> bool:
    return role in _EDIT_ROLES


def can_publish(role: str) -> bool:
    return role in _PUBLISH_ROLES


def can_manage_team(role: str) -> bool:
    return role in _MANAGE_TEAM_ROLES


def can_manage_integrations(role: str) -> bool:
    return role in _MANAGE_INTEGRATIONS_ROLES


def generate_token(nbytes: int = 32) -> str:
    """Return an unguessable URL-safe token (>= 32 chars)."""
    return secrets.token_urlsafe(nbytes)


def hash_share_password(password: str) -> str:
    """Salted PBKDF2 hash for optional share-link passwords."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()
    return f"pbkdf2${salt}${digest}"


def verify_share_password(password: str, stored: str | None) -> bool:
    if not stored:
        return True
    try:
        scheme, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()
    return hmac.compare_digest(digest, expected)


@dataclass(frozen=True)
class Membership:
    member_id: int
    workspace_id: str
    email: str
    role: str
    status: str

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class WorkspaceService:
    """Resolves and enforces workspace membership for a caller email."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def resolve(
        self, email: str | None, preferred_workspace_id: str | None = None
    ) -> Membership | None:
        """Return the caller's active membership, self-provisioning into the
        caller's private workspace as needed. Returns ``None`` when no email is
        known or when the caller is denied (invite-only mode, not an admin).

        Provisioning rules for a caller with no membership:
        - if the trusted proxy provides a workspace id, it becomes the caller's
          private workspace id;
        - default workspace has no owner and no proxy workspace was provided ->
          caller becomes owner of ``default`` for legacy recovery;
        - caller's email is a configured admin -> owner (always recoverable);
        - otherwise, if ``workspace_auto_join`` is on -> owner of a deterministic
          private workspace derived from email; else denied.
        """
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        preferred = self._normalize_preferred_workspace_id(preferred_workspace_id)
        admin_emails = self.settings.admin_email_set()
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            if preferred:
                member = repo.get_member_in_workspace(preferred, normalized)
                if member is not None and getattr(member, "status", None) == "active":
                    return _to_membership(member)
                if (
                    not self.settings.workspace_auto_join
                    and normalized not in admin_emails
                ):
                    return None
                try:
                    member = repo.add_member(
                        workspace_id=preferred,
                        email=normalized,
                        role="owner",
                        status="active",
                        invited_by=None,
                    )
                    return _to_membership(member)
                except IntegrityError:
                    session.rollback()
                    member = repo.get_member_in_workspace(preferred, normalized)
                    if (
                        member is not None
                        and getattr(member, "status", None) == "active"
                    ):
                        return _to_membership(member)
                    return None

            member = repo.get_active_member_by_email(normalized)
            if member is not None:
                return _to_membership(member)
            workspace_role = self._workspace_role_for_new_member(
                repo, normalized, admin_emails
            )
            if workspace_role is None:
                return None
            workspace_id, role = workspace_role
            try:
                member = repo.add_member(
                    workspace_id=workspace_id,
                    email=normalized,
                    role=role,
                    status="active",
                    invited_by=None,
                )
                return _to_membership(member)
            except IntegrityError:
                # A concurrent request inserted the same member; fall through to
                # re-read it in a fresh session.
                session.rollback()
        with session_scope() as session:
            member = WorkspaceRepository(session).get_active_member_by_email(
                normalized
            )
            return _to_membership(member) if member is not None else None

    @staticmethod
    def _normalize_preferred_workspace_id(workspace_id: str | None) -> str | None:
        value = (workspace_id or "").strip()
        if not value or value == DEFAULT_WORKSPACE_ID:
            return None
        return value[:200]

    @staticmethod
    def private_workspace_id(email: str) -> str:
        normalized = email.strip().lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
        return f"user-{digest}"

    def _workspace_role_for_new_member(
        self,
        repo: WorkspaceRepository,
        email: str,
        admin_emails: set[str],
    ) -> tuple[str, str] | None:
        if repo.count_owners(DEFAULT_WORKSPACE_ID) == 0:
            return (DEFAULT_WORKSPACE_ID, "owner")
        if email in admin_emails:
            return (DEFAULT_WORKSPACE_ID, "owner")
        if self.settings.workspace_auto_join:
            return (self.private_workspace_id(email), "owner")
        return None

    def require_membership(
        self, email: str | None, preferred_workspace_id: str | None = None
    ) -> Membership:
        membership = self.resolve(email, preferred_workspace_id)
        if membership is None:
            raise WorkspaceAccessError(
                "У вас нет доступа к этому workspace.", status=403
            )
        return membership

    def require_workspace(
        self, email: str | None, workspace_id: str
    ) -> Membership:
        membership = self.require_membership(email)
        if membership.workspace_id != workspace_id:
            # Hide the existence of another workspace.
            raise WorkspaceAccessError(
                "У вас нет доступа к этому workspace.", status=404
            )
        return membership

    @staticmethod
    def require_can_manage_team(membership: Membership) -> None:
        if not can_manage_team(membership.role):
            raise WorkspaceAccessError(
                "Управление командой доступно только владельцу или администратору.",
                status=403,
            )

    @staticmethod
    def require_can_edit(membership: Membership) -> None:
        if not can_edit(membership.role):
            raise WorkspaceAccessError(
                "У вашей роли нет прав на редактирование.", status=403
            )

    @staticmethod
    def require_can_publish(membership: Membership) -> None:
        if not can_publish(membership.role):
            raise WorkspaceAccessError(
                "У вашей роли нет прав на публикацию.", status=403
            )


def _to_membership(member: object) -> Membership:
    return Membership(
        member_id=int(getattr(member, "id")),
        workspace_id=str(getattr(member, "workspace_id")),
        email=str(getattr(member, "email")),
        role=str(getattr(member, "role")),
        status=str(getattr(member, "status")),
    )
