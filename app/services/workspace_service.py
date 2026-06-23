"""Workspace / team access control.

This is the single source of truth for *who* may do *what* in a workspace.
Identity is email-based (the Next proxy verifies the Supabase session and
forwards the verified email); membership rows decide access.

Phase-1 bootstrap: the app was single-tenant, so all legacy data lives in the
``default`` workspace. The first authenticated caller with no membership becomes
the owner of that workspace; everyone else must be invited.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

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

    def resolve(self, email: str | None) -> Membership | None:
        """Return the caller's active membership, provisioning the default
        workspace owner on first use. Returns ``None`` when no email is known.
        """
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        with session_scope() as session:
            repo = WorkspaceRepository(session)
            member = repo.get_active_member_by_email(normalized)
            if member is not None:
                return _to_membership(member)
            # Bootstrap: the very first caller owns the default workspace.
            if not repo.has_any_member(DEFAULT_WORKSPACE_ID):
                member = repo.add_member(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    email=normalized,
                    role="owner",
                    status="active",
                    invited_by=None,
                )
                return _to_membership(member)
        return None

    def require_membership(self, email: str | None) -> Membership:
        membership = self.resolve(email)
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
