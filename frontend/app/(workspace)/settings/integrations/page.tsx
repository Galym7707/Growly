"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { LoadingState, PageHeader, Status } from "@/components/ui";
import { apiRequest, formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { SocialStatus } from "@/lib/integrations";

export default function IntegrationsPage() {
  const { locale, t } = useLanguage();
  const [social, setSocial] = useState<SocialStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState("");
  const [username, setUsername] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeKind, setNoticeKind] = useState<"success" | "error">("success");

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    try {
      const status = await apiRequest<SocialStatus>(
        "/integrations/social/status?platform=instagram",
      );
      setSocial(status);
      setUsername(status.request?.requested_username || "");
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function flash(message: string, kind: "success" | "error" = "success") {
    setNotice(message);
    setNoticeKind(kind);
  }

  function failureMessage(value: unknown): string {
    return value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
  }

  async function sendRequest() {
    if (!username.trim()) {
      flash(t("Укажите ваш Instagram username."), "error");
      return;
    }
    setBusy("request");
    setNotice("");
    try {
      const status = await apiRequest<SocialStatus>(
        "/integrations/social/request",
        {
          method: "POST",
          body: JSON.stringify({ platform: "instagram", username: username.trim() }),
        },
      );
      setSocial(status);
      flash(t("Заявка отправлена."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function cancelRequest() {
    if (!social?.request?.id) return;
    setBusy("cancel");
    setNotice("");
    try {
      const status = await apiRequest<SocialStatus>(
        `/integrations/social/request/${social.request.id}`,
        { method: "DELETE" },
      );
      setSocial(status);
      flash(t("Заявка отменена."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function disconnect() {
    setBusy("disconnect");
    setNotice("");
    try {
      const status = await apiRequest<SocialStatus>(
        "/integrations/social/disconnect",
        { method: "POST", body: JSON.stringify({ platform: "instagram" }) },
      );
      setSocial(status);
      flash(t("Instagram отключён."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  if (loading) {
    return (
      <div className="workspace-page">
        <LoadingState />
      </div>
    );
  }

  const state = social?.state ?? "not_connected";

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Конфигурация")}
        title={t("Интеграции")}
        description={t("Подключения Growly: автопостинг в ваши соцсети.")}
        action={
          <Link className="button button-secondary" href="/settings">
            {t("Назад к настройкам")}
          </Link>
        }
      />

      {failed ? (
        <div className="feedback feedback-error">
          {t("Не удалось загрузить интеграции. Попробуйте ещё раз.")}
          <div className="feedback-actions">
            <button className="button button-secondary button-small" onClick={load} type="button">
              {t("Повторить")}
            </button>
          </div>
        </div>
      ) : null}
      {notice ? (
        <div className={`feedback feedback-${noticeKind === "error" ? "error" : "success"}`}>
          {notice}
        </div>
      ) : null}

      <section className="integration-card integration-card-wide">
        <div className="integration-card-head">
          <h2>{t("Instagram автопостинг")}</h2>
          <Status value={state === "connected" ? "active" : state === "failed" ? "failed" : "pending"}>
            {state === "connected"
              ? t("Подключено")
              : state === "pending" || state === "in_progress"
                ? t("Ожидает подключения")
                : state === "failed"
                  ? t("Ошибка")
                  : t("Не подключено")}
          </Status>
        </div>

        <p className="muted">
          {t("Growly может автоматически публиковать посты в ваш Instagram. Подключение выполняется безопасно через официальный вход Instagram/Meta. Мы никогда не просим и не храним ваш пароль.")}
        </p>
        <p className="integration-scheme">Growly → Blotato → Instagram</p>
        <p className="muted plan-note-muted">
          {t("Подключение выполняется вручную администратором Growly на MVP-этапе. Вы не передаёте пароль. Вы сами подтверждаете доступ через официальный экран Instagram/Meta.")}
        </p>

        {/* A) not_connected */}
        {state === "not_connected" ? (
          <div className="integration-block">
            <h3>{t("Instagram не подключен")}</h3>
            <p className="muted">
              {t("Отправьте заявку, и мы поможем подключить ваш Instagram к автопостингу. Подключение проходит через официальный OAuth, без передачи пароля.")}
            </p>
            <label className="full">
              <span>{t("Instagram username")}</span>
              <input
                onChange={(event) => setUsername(event.target.value)}
                placeholder="@your_business"
                type="text"
                value={username}
              />
            </label>
            <div className="integration-actions">
              <button
                className="button button-primary"
                disabled={busy !== ""}
                onClick={sendRequest}
                type="button"
              >
                {busy === "request" ? t("Отправляем") : t("Отправить заявку на подключение")}
              </button>
            </div>
          </div>
        ) : null}

        {/* B) pending / in_progress */}
        {state === "pending" || state === "in_progress" ? (
          <div className="integration-block">
            <h3>{t("Заявка на подключение отправлена")}</h3>
            <p className="muted">
              {t("Администратор Growly свяжется с вами и поможет безопасно подключить Instagram через OAuth. Не отправляйте пароль от Instagram.")}
            </p>
            <ul className="integration-facts">
              <li>
                {t("Instagram username")}: <strong>{social?.request?.requested_username || "—"}</strong>
              </li>
              <li>
                {t("Статус")}: <strong>{t("Ожидает подключения")}</strong>
              </li>
            </ul>
            <div className="integration-actions">
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={load}
                type="button"
              >
                {t("Обновить статус")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={cancelRequest}
                type="button"
              >
                {busy === "cancel" ? t("Отменяем") : t("Отменить заявку")}
              </button>
            </div>
          </div>
        ) : null}

        {/* C) connected */}
        {state === "connected" ? (
          <div className="integration-block">
            <h3>{t("Instagram подключен")}</h3>
            <p className="muted">
              {t("Growly может публиковать посты в этот аккаунт через Blotato.")}
            </p>
            <ul className="integration-facts">
              <li>
                {t("Аккаунт")}: <strong>{social?.account?.display_name || social?.account?.username || "—"}</strong>
              </li>
              <li>
                {t("ID аккаунта")}: <strong>{social?.account?.external_account_id || "—"}</strong>
              </li>
              <li>
                {t("Статус")}: <strong>{t("Подключено")}</strong>
              </li>
              {social?.account?.connected_at ? (
                <li>
                  {t("Подключён")}: <strong>{formatDate(social.account.connected_at, locale)}</strong>
                </li>
              ) : null}
            </ul>
            <div className="integration-actions">
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={load}
                type="button"
              >
                {t("Проверить подключение")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={disconnect}
                type="button"
              >
                {busy === "disconnect" ? t("Отключаем") : t("Отключить")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={disconnect}
                type="button"
              >
                {t("Сменить аккаунт")}
              </button>
            </div>
          </div>
        ) : null}

        {/* D) failed */}
        {state === "failed" ? (
          <div className="integration-block">
            <h3>{t("Не удалось подключить Instagram")}</h3>
            <p className="muted">
              {social?.request?.admin_note ||
                t("Подключение не удалось. Отправьте заявку повторно.")}
            </p>
            <div className="integration-actions">
              <button
                className="button button-primary"
                disabled={busy !== ""}
                onClick={() => {
                  setUsername(social?.request?.requested_username || "");
                  void sendRequest();
                }}
                type="button"
              >
                {t("Повторить заявку")}
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
