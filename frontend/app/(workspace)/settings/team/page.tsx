"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { InviteModal } from "@/components/team/invite-modal";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import { apiRequest, formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import {
  ROLE_LABELS,
  useWorkspace,
  type WorkspaceRole,
} from "@/lib/workspace";

type Member = {
  id: number;
  email: string;
  role: WorkspaceRole;
  status: string;
  joined_at: string | null;
  created_at: string | null;
};

type Invitation = {
  id: number;
  email: string;
  role: string;
  token: string;
  status: string;
  invite_path: string;
  expires_at: string | null;
};

export default function TeamPage() {
  const { locale, t } = useLanguage();
  const { workspace } = useWorkspace();
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const canManage = Boolean(workspace?.permissions.can_manage_team);
  const workspaceId = workspace?.workspace_id;

  const load = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{
        members: Member[];
        invitations: Invitation[];
      }>(`/workspaces/${encodeURIComponent(workspaceId)}/members`);
      setMembers(response.members || []);
      setInvitations(response.invitations || []);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function changeRole(member: Member, role: WorkspaceRole) {
    if (!workspaceId) return;
    setBusyId(member.id);
    setError("");
    try {
      await apiRequest(
        `/workspaces/${encodeURIComponent(workspaceId)}/members/${member.id}/role`,
        { method: "PATCH", body: JSON.stringify({ role }) },
      );
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusyId(null);
    }
  }

  async function removeMember(member: Member) {
    if (!workspaceId) return;
    setBusyId(member.id);
    setError("");
    try {
      await apiRequest(
        `/workspaces/${encodeURIComponent(workspaceId)}/members/${member.id}`,
        { method: "DELETE" },
      );
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusyId(null);
    }
  }

  async function revokeInvite(invitation: Invitation) {
    if (!workspaceId) return;
    setBusyId(-invitation.id);
    setError("");
    try {
      await apiRequest(
        `/workspaces/${encodeURIComponent(workspaceId)}/invitations/${invitation.id}`,
        { method: "DELETE" },
      );
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusyId(null);
    }
  }

  async function copyInvite(invitation: Invitation) {
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}${invitation.invite_path}`,
      );
    } catch {
      setError(t("Не удалось скопировать ссылку"));
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Рабочее пространство")}
        title={t("Команда")}
        description={t("Участники этого workspace и их роли.")}
        action={
          canManage ? (
            <button
              className="button button-primary"
              onClick={() => setInviteOpen(true)}
              type="button"
            >
              <Icon name="users" />
              {t("Поделиться с командой")}
            </button>
          ) : undefined
        }
      />

      {loading ? <LoadingState label={t("Загрузка данных")} /> : null}
      {error && !loading ? <ErrorState message={error} retry={load} /> : null}

      {!loading && !error ? (
        <>
          <section className="workspace-section">
            <div className="form-panel">
              <h2>{t("Участники")}</h2>
              <div className="team-table">
                <div className="team-row team-row-head">
                  <span>Email</span>
                  <span>{t("Роль")}</span>
                  <span>{t("Статус")}</span>
                  <span>{t("Присоединился")}</span>
                  <span />
                </div>
                {members.map((member) => (
                  <div className="team-row" key={member.id}>
                    <span className="team-email">{member.email}</span>
                    <span>
                      {canManage ? (
                        <select
                          disabled={busyId === member.id}
                          onChange={(event) =>
                            changeRole(
                              member,
                              event.target.value as WorkspaceRole,
                            )
                          }
                          value={member.role}
                        >
                          <option value="owner">{t(ROLE_LABELS.owner)}</option>
                          <option value="admin">{t(ROLE_LABELS.admin)}</option>
                          <option value="editor">{t(ROLE_LABELS.editor)}</option>
                          <option value="viewer">{t(ROLE_LABELS.viewer)}</option>
                        </select>
                      ) : (
                        t(ROLE_LABELS[member.role])
                      )}
                    </span>
                    <Status value={member.status === "active" ? "active" : "pending"}>
                      {member.status === "active"
                        ? t("Активен")
                        : t("Приглашён")}
                    </Status>
                    <span className="muted">
                      {formatDate(member.joined_at || member.created_at, locale)}
                    </span>
                    <span className="team-actions">
                      {canManage ? (
                        <button
                          aria-label={t("Удалить участника")}
                          className="icon-button"
                          disabled={busyId === member.id}
                          onClick={() => removeMember(member)}
                          title={t("Удалить участника")}
                          type="button"
                        >
                          <Icon name="close" />
                        </button>
                      ) : null}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {invitations.length ? (
            <section className="workspace-section">
              <div className="form-panel">
                <h2>{t("Приглашения")}</h2>
                <div className="team-table">
                  {invitations.map((invitation) => (
                    <div className="team-row team-row-invite" key={invitation.id}>
                      <span className="team-email">{invitation.email}</span>
                      <span>{t(ROLE_LABELS[invitation.role as WorkspaceRole])}</span>
                      <Status value="pending">{t("Ожидает")}</Status>
                      <span className="team-actions">
                        <button
                          className="button button-secondary button-small"
                          onClick={() => copyInvite(invitation)}
                          type="button"
                        >
                          <Icon name="external" />
                          {t("Скопировать ссылку")}
                        </button>
                        {canManage ? (
                          <button
                            className="button button-secondary button-small"
                            disabled={busyId === -invitation.id}
                            onClick={() => revokeInvite(invitation)}
                            type="button"
                          >
                            {t("Отменить приглашение")}
                          </button>
                        ) : null}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ) : null}

          <section className="workspace-section">
            <div className="form-panel">
              <p className="muted">
                {t("Notion используется как внутренний инструмент синхронизации и не является публичным кабинетом клиента.")}
              </p>
              <Link className="text-link" href="/settings/integrations">
                {t("Открыть интеграции")}
                <Icon name="arrow" />
              </Link>
            </div>
          </section>
        </>
      ) : null}

      {inviteOpen && workspaceId ? (
        <InviteModal
          workspaceId={workspaceId}
          onClose={() => setInviteOpen(false)}
          onCreated={load}
        />
      ) : null}
    </div>
  );
}
