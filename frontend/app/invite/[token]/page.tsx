"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { apiRequest } from "@/lib/api";
import { isLocalAuthBypassAllowed } from "@/lib/auth-config";
import { useLanguage } from "@/lib/i18n";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
import { ROLE_LABELS, type WorkspaceRole } from "@/lib/workspace";

type InvitationInfo = {
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  status: "pending" | "accepted" | "expired" | "revoked";
};

export default function InvitePage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const router = useRouter();
  const { t } = useLanguage();

  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [authed, setAuthed] = useState(false);
  const [accepting, setAccepting] = useState(false);

  const nextPath = `/invite/${encodeURIComponent(token)}`;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<InvitationInfo>(
        `/invitations/${encodeURIComponent(token)}`,
      );
      setInfo(response);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }

    if (!isSupabaseConfigured()) {
      setAuthed(isLocalAuthBypassAllowed());
      return;
    }
    const { data } = await createClient().auth.getUser();
    setAuthed(Boolean(data.user));
  }, [token, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function accept() {
    setAccepting(true);
    setError("");
    try {
      const response = await apiRequest<{ workspace_id: string }>(
        `/invitations/${encodeURIComponent(token)}/accept`,
        { method: "POST", body: JSON.stringify({}) },
      );
      router.push(`/dashboard?workspaceId=${encodeURIComponent(response.workspace_id)}`);
      router.refresh();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
      setAccepting(false);
    }
  }

  const expired = info?.status === "expired";
  const revoked = info?.status === "revoked";
  const invalid = expired || revoked;

  return (
    <main className="auth-page">
      <div className="auth-brand">
        <Logo />
        <LanguageSwitcher compact />
        <div>
          <p className="eyebrow">{t("Приглашение в Growly")}</p>
          <h1>{t("Присоединяйтесь к команде")}</h1>
          <p>
            {t("Вас пригласили работать с отчётами, контент-планом и черновиками внутри Growly.")}
          </p>
        </div>
        <Link className="text-link" href="/">
          {t("Вернуться на главную")}
          <Icon name="arrow" />
        </Link>
      </div>

      <div className="auth-panel">
        <div className="invite-panel">
          <p className="eyebrow">{t("Приглашение")}</p>
          <h2>{t("Пригласить участника")}</h2>

          {loading ? <p className="muted">{t("Загрузка данных")}…</p> : null}

          {!loading && expired ? (
            <p className="feedback feedback-error">
              {t("Приглашение истекло. Попросите владельца отправить новое.")}
            </p>
          ) : null}
          {!loading && revoked ? (
            <p className="feedback feedback-error">
              {t("Приглашение больше недействительно.")}
            </p>
          ) : null}

          {!loading && info && !invalid ? (
            <>
              <div className="invite-summary">
                <div>
                  <span className="muted">Email</span>
                  <strong>{info.email}</strong>
                </div>
                <div>
                  <span className="muted">{t("Роль")}</span>
                  <strong>{t(ROLE_LABELS[info.role])}</strong>
                </div>
              </div>

              {error ? <p className="form-error">{error}</p> : null}

              {authed ? (
                <button
                  className="button button-primary button-wide"
                  disabled={accepting}
                  onClick={accept}
                  type="button"
                >
                  <Icon name={accepting ? "sync" : "check"} />
                  {accepting ? t("Принимаем") : t("Принять приглашение")}
                </button>
              ) : (
                <div className="invite-auth-actions">
                  <p className="muted">
                    {t("Войдите или зарегистрируйтесь, чтобы принять приглашение.")}
                  </p>
                  <Link
                    className="button button-primary button-wide"
                    href={`/login?next=${encodeURIComponent(nextPath)}`}
                  >
                    {t("Войти")}
                  </Link>
                  <Link
                    className="button button-secondary button-wide"
                    href={`/login?mode=register&next=${encodeURIComponent(nextPath)}`}
                  >
                    {t("Зарегистрироваться")}
                  </Link>
                </div>
              )}
            </>
          ) : null}

          {!loading && !info && error ? (
            <p className="feedback feedback-error">{error}</p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
