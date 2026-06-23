from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import ShareLink, WorkspaceInvitation, WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -- members -----------------------------------------------------------

    def get_active_member_by_email(self, email: str) -> WorkspaceMember | None:
        normalized = email.strip().lower()
        return self.session.scalar(
            select(WorkspaceMember)
            .where(
                func.lower(WorkspaceMember.email) == normalized,
                WorkspaceMember.status == "active",
            )
            .order_by(WorkspaceMember.created_at)
            .limit(1)
        )

    def get_member(self, member_id: int) -> WorkspaceMember | None:
        return self.session.get(WorkspaceMember, member_id)

    def get_member_in_workspace(
        self, workspace_id: str, email: str
    ) -> WorkspaceMember | None:
        normalized = email.strip().lower()
        return self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                func.lower(WorkspaceMember.email) == normalized,
            )
        )

    def has_any_member(self, workspace_id: str) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
            )
            or 0
        ) > 0

    def list_members(self, workspace_id: str) -> list[WorkspaceMember]:
        return list(
            self.session.scalars(
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
                .order_by(WorkspaceMember.created_at)
            )
        )

    def add_member(
        self,
        *,
        workspace_id: str,
        email: str,
        role: str,
        status: str = "active",
        invited_by: str | None = None,
        user_id: int | None = None,
    ) -> WorkspaceMember:
        now = datetime.now(UTC)
        member = WorkspaceMember(
            workspace_id=workspace_id,
            email=email.strip().lower(),
            role=role,
            status=status,
            invited_by=invited_by,
            user_id=user_id,
            invited_at=now if status == "invited" else None,
            joined_at=now if status == "active" else None,
        )
        self.session.add(member)
        self.session.flush()
        return member

    def update_member_role(
        self, member: WorkspaceMember, role: str
    ) -> WorkspaceMember:
        member.role = role
        self.session.flush()
        return member

    def remove_member(self, member: WorkspaceMember) -> WorkspaceMember:
        member.status = "removed"
        self.session.flush()
        return member

    def count_owners(self, workspace_id: str) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(WorkspaceMember)
                .where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == "owner",
                    WorkspaceMember.status == "active",
                )
            )
            or 0
        )

    # -- invitations -------------------------------------------------------

    def create_invitation(
        self,
        *,
        workspace_id: str,
        email: str,
        role: str,
        token: str,
        invited_by: str | None,
        expires_at: datetime | None,
    ) -> WorkspaceInvitation:
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email.strip().lower(),
            role=role,
            token=token,
            status="pending",
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        self.session.flush()
        return invitation

    def get_invitation_by_token(self, token: str) -> WorkspaceInvitation | None:
        return self.session.scalar(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.token == token
            )
        )

    def get_invitation(self, invitation_id: int) -> WorkspaceInvitation | None:
        return self.session.get(WorkspaceInvitation, invitation_id)

    def list_invitations(
        self, workspace_id: str, status: str | None = None
    ) -> list[WorkspaceInvitation]:
        statement = select(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == workspace_id
        )
        if status:
            statement = statement.where(WorkspaceInvitation.status == status)
        statement = statement.order_by(desc(WorkspaceInvitation.created_at))
        return list(self.session.scalars(statement))

    def set_invitation_status(
        self,
        invitation: WorkspaceInvitation,
        status: str,
        accepted_at: datetime | None = None,
    ) -> WorkspaceInvitation:
        invitation.status = status
        if accepted_at is not None:
            invitation.accepted_at = accepted_at
        self.session.flush()
        return invitation

    # -- share links -------------------------------------------------------

    def create_share_link(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_id: int | None,
        token: str,
        password_hash: str | None,
        expires_at: datetime | None,
        created_by: str | None,
    ) -> ShareLink:
        link = ShareLink(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            token=token,
            access_level="view",
            password_hash=password_hash,
            expires_at=expires_at,
            is_active=True,
            created_by=created_by,
        )
        self.session.add(link)
        self.session.flush()
        return link

    def get_share_link_by_token(self, token: str) -> ShareLink | None:
        return self.session.scalar(
            select(ShareLink).where(ShareLink.token == token)
        )

    def get_share_link(self, link_id: int) -> ShareLink | None:
        return self.session.get(ShareLink, link_id)

    def deactivate_share_link(self, link: ShareLink) -> ShareLink:
        link.is_active = False
        self.session.flush()
        return link
