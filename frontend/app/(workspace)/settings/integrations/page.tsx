"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FriendlyError } from "@/components/friendly-error";
import { LoadingState, PageHeader, Status } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import {
  PUBLISH_PLATFORMS,
  accountForPlatform,
  platformStateLabel,
  type BlotatoAccount,
  type BlotatoStatus,
  type IntegrationsStatus,
} from "@/lib/integrations";
import { useLanguage } from "@/lib/i18n";

export default function IntegrationsPage() {
  const { t } = useLanguage();
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [blotato, setBlotato] = useState<BlotatoStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<string>("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    setErrorDebug(null);
    try {
      const [statusResp, blotatoResp, accountsResp] = await Promise.all([
        apiRequest<IntegrationsStatus>("/integrations/status"),
        apiRequest<BlotatoStatus>("/integrations/blotato/status"),
        apiRequest<{ accounts: BlotatoAccount[] }>("/integrations/blotato/accounts"),
      ]);
      setStatus(statusResp);
      setBlotato(blotatoResp);
      setAccounts(accountsResp.accounts || []);
    } catch (value) {
      setFailed(true);
      setErrorDebug(apiErrorDebugInfo(value));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function refreshAccounts() {
    setBusy("accounts");
    setNotice("");
    try {
      const response = await apiRequest<{ accounts: BlotatoAccount[] }>(
        "/integrations/blotato/accounts",
      );
      setAccounts(response.accounts || []);
      setNotice(t("Список аккаунтов обновлён."));
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy("");
    }
  }

  async function testBlotato() {
    setBusy("test");
    setNotice("");
    try {
      const response = await apiRequest<{ ok: boolean; message: string; accounts_count: number }>(
        "/integrations/blotato/test",
        { method: "POST", body: JSON.stringify({}) },
      );
      setNotice(`${t(response.message)} · ${t("{count} источников", { count: response.accounts_count })}`);
      await load();
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy("");
    }
  }

  if (loading) return <LoadingStatePage />;

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Конфигурация")}
        title={t("Интеграции")}
        description={t("Подключения Growly: Telegram, Notion и автопубликация в соцсети.")}
        action={
          <Link className="button button-secondary" href="/settings">
            {t("Назад к настройкам")}
          </Link>
        }
      />

      {failed ? <FriendlyError debug={errorDebug} onRetry={load} /> : null}
      {notice ? <div className="feedback feedback-success">{notice}</div> : null}

      <div className="integration-grid">
        <section className="integration-card">
          <div className="integration-card-head">
            <h2>Telegram</h2>
            <Status value={status?.telegram.connected ? "active" : "disabled"}>
              {status?.telegram.connected ? t("Подключено") : t("Не подключено")}
            </Status>
          </div>
          <p className="muted">
            {status?.telegram.channel_id
              ? `${t("Канал")}: ${status.telegram.channel_id}`
              : t("Канал публикации не указан.")}
          </p>
          <div className="integration-actions">
            <button
              className="button button-secondary button-small"
              disabled={busy !== ""}
              onClick={load}
              type="button"
            >
              {t("Проверить публикацию")}
            </button>
          </div>
        </section>

        <section className="integration-card">
          <div className="integration-card-head">
            <h2>Notion</h2>
            <Status value={status?.notion.connected ? "active" : "disabled"}>
              {status?.notion.connected ? t("Подключено") : t("Не подключено")}
            </Status>
          </div>
          <p className="muted">
            {status?.notion.root_configured
              ? t("Корневая страница настроена.")
              : t("Корневая страница не настроена.")}
          </p>
          <div className="integration-actions">
            <button
              className="button button-secondary button-small"
              disabled={busy !== ""}
              onClick={load}
              type="button"
            >
              {t("Проверить синхронизацию")}
            </button>
          </div>
        </section>

        <section className="integration-card integration-card-wide">
          <div className="integration-card-head">
            <h2>Blotato</h2>
            <Status value={blotato?.connected ? "active" : "disabled"}>
              {blotato?.connected ? t("Подключено") : t("Не подключено")}
            </Status>
          </div>
          <ul className="integration-facts">
            <li>
              {t("API-ключ настроен")}:{" "}
              <strong>{blotato?.api_key_configured ? t("да") : t("нет")}</strong>
            </li>
            <li>
              {t("Аккаунтов подключено")}: <strong>{blotato?.accounts_count ?? 0}</strong>
            </li>
          </ul>
          <div className="integration-actions">
            <button
              className="button button-secondary button-small"
              disabled={busy !== ""}
              onClick={testBlotato}
              type="button"
            >
              {busy === "test" ? t("Проверяем") : t("Проверить подключение")}
            </button>
            <button
              className="button button-secondary button-small"
              disabled={busy !== ""}
              onClick={refreshAccounts}
              type="button"
            >
              {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
            </button>
            <Link
              className="button button-secondary button-small"
              href="/settings/integrations/blotato"
            >
              {t("Настроить публикацию")}
            </Link>
          </div>
        </section>
      </div>

      <section className="workspace-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{t("Социальные сети")}</p>
            <h2>{t("Подключённые аккаунты")}</h2>
          </div>
          <button
            className="button button-secondary button-small"
            disabled={busy !== ""}
            onClick={refreshAccounts}
            type="button"
          >
            {t("Обновить список аккаунтов")}
          </button>
        </div>

        {blotato && !blotato.enabled ? (
          <p className="plan-note plan-note-muted">
            {t("Автопубликация не подключена. Growly может подготовить пакет для ручной публикации.")}
          </p>
        ) : null}

        <div className="account-grid">
          {PUBLISH_PLATFORMS.filter((p) => p.provider === "blotato").map((platform) => {
            const account = accountForPlatform(accounts, platform.slug);
            const state = platformStateLabel(status?.blotato ?? null, accounts, platform.slug);
            return (
              <article className="account-card" key={platform.slug}>
                <div className="account-card-head">
                  <h3>{platform.label}</h3>
                  <Status value={state === "connected" ? "active" : "disabled"}>
                    {state === "connected"
                      ? t("Подключено")
                      : state === "disabled"
                        ? t("Отключено")
                        : t("Не подключено")}
                  </Status>
                </div>
                <p className="muted">
                  {account
                    ? account.display_name || account.name
                    : t("Нет подключённого аккаунта.")}
                </p>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function LoadingStatePage() {
  return (
    <div className="workspace-page">
      <LoadingState />
    </div>
  );
}
