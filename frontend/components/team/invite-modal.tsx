"use client";

import { FormEvent, useState } from "react";
import { Icon } from "@/components/icons";
import { apiRequest } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

type InviteRole = "viewer" | "editor" | "admin";

type Invitation = {
  email: string;
  role: string;
  token: string;
  invite_path: string;
};

export function InviteModal({
  workspaceId,
  onClose,
  onCreated,
}: {
  workspaceId: string;
  onClose: () => void;
  onCreated?: () => void;
}) {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<InviteRole>("viewer");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Invitation | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const [copied, setCopied] = useState(false);

  const inviteUrl = created
    ? `${typeof window !== "undefined" ? window.location.origin : ""}${created.invite_path}`
    : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await apiRequest<{
        invitation: Invitation;
        email_sent?: boolean;
      }>(`/workspaces/${encodeURIComponent(workspaceId)}/invitations`, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role, message }),
      });
      setCreated(response.invitation);
      setEmailSent(Boolean(response.email_sent));
      onCreated?.();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setSubmitting(false);
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError(t("Не удалось скопировать ссылку"));
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="modal-card"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal-head">
          <h2>{t("Пригласить участника")}</h2>
          <button
            aria-label={t("Закрыть")}
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="close" />
          </button>
        </div>

        {created ? (
          <div className="invite-created">
            <p className="feedback feedback-success">
              {emailSent
                ? t("Приглашение отправлено на {email}.", { email: created.email })
                : t("Приглашение создано")}
            </p>
            <p className="muted">
              {emailSent
                ? t("Можно также скопировать ссылку и отправить вручную.")
                : t("Скопируйте ссылку и отправьте её участнику ({email}).", {
                    email: created.email,
                  })}
            </p>
            <div className="copy-row">
              <input readOnly value={inviteUrl} />
              <button
                className="button button-primary"
                onClick={copyLink}
                type="button"
              >
                <Icon name={copied ? "check" : "external"} />
                {copied ? t("Скопировано") : t("Скопировать ссылку")}
              </button>
            </div>
            <div className="form-actions">
              <button
                className="button button-secondary"
                onClick={onClose}
                type="button"
              >
                {t("Закрыть")}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={submit}>
            <label>
              <span>Email</span>
              <input
                autoFocus
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.kz"
                required
                type="email"
                value={email}
              />
            </label>
            <label>
              <span>{t("Роль")}</span>
              <select
                onChange={(event) => setRole(event.target.value as InviteRole)}
                value={role}
              >
                <option value="viewer">{t("Только просмотр")}</option>
                <option value="editor">{t("Редактор")}</option>
                <option value="admin">{t("Администратор")}</option>
              </select>
            </label>
            <label>
              <span>{t("Сообщение (необязательно)")}</span>
              <textarea
                onChange={(event) => setMessage(event.target.value)}
                rows={3}
                value={message}
              />
            </label>
            {error ? <p className="form-error">{error}</p> : null}
            <div className="form-actions">
              <button
                className="button button-secondary"
                onClick={onClose}
                type="button"
              >
                {t("Отмена")}
              </button>
              <button
                className="button button-primary"
                disabled={submitting || !email.trim()}
                type="submit"
              >
                <Icon name={submitting ? "sync" : "arrow"} />
                {submitting ? t("Отправляем") : t("Отправить приглашение")}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
