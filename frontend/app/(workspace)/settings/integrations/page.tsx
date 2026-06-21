"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FriendlyError } from "@/components/friendly-error";
import { LoadingState, PageHeader, Status } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import {
  accountsForPlatform,
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
  const [noticeKind, setNoticeKind] = useState<"success" | "error">("success");
  const [apiKey, setApiKey] = useState("");
  const [igAccount, setIgAccount] = useState("");

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
      setIgAccount(blotatoResp.instagram?.account_id || "");
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

  function flash(message: string, kind: "success" | "error" = "success") {
    setNotice(message);
    setNoticeKind(kind);
  }

  function failureMessage(value: unknown): string {
    return value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
  }

  const igAccounts = useMemo(
    () => accountsForPlatform(accounts, "instagram"),
    [accounts],
  );

  // State machine: A = no key, B = key but no IG account, C = IG connected.
  const igState: "a" | "b" | "c" = !blotato?.api_key_configured
    ? "a"
    : blotato?.instagram?.selected
      ? "c"
      : "b";

  async function saveApiKey() {
    if (apiKey.trim().length < 8) {
      flash(t("Введите корректный API-ключ Blotato."), "error");
      return;
    }
    setBusy("connect");
    setNotice("");
    try {
      const response = await apiRequest<{ accounts_count: number }>(
        "/integrations/blotato/connect",
        { method: "POST", body: JSON.stringify({ api_key: apiKey.trim() }) },
      );
      setApiKey("");
      flash(
        t("Blotato подключён. Найдено аккаунтов: {count}.", {
          count: response.accounts_count,
        }),
      );
      await load();
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function refreshAccounts() {
    setBusy("accounts");
    setNotice("");
    try {
      const response = await apiRequest<{ accounts: BlotatoAccount[] }>(
        "/integrations/blotato/accounts",
      );
      setAccounts(response.accounts || []);
      flash(t("Список аккаунтов обновлён."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function selectInstagram() {
    if (!igAccount) {
      flash(t("Выберите Instagram аккаунт из списка."), "error");
      return;
    }
    setBusy("select");
    setNotice("");
    try {
      await apiRequest("/integrations/blotato/select-account", {
        method: "POST",
        body: JSON.stringify({ platform: "instagram", account_id: igAccount }),
      });
      flash(t("Instagram аккаунт сохранён."));
      await load();
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function testConnection() {
    setBusy("test");
    setNotice("");
    try {
      const response = await apiRequest<{ message: string; accounts_count: number }>(
        "/integrations/blotato/test",
        { method: "POST", body: JSON.stringify({}) },
      );
      flash(
        `${t(response.message)} · ${t("{count} источников", { count: response.accounts_count })}`,
      );
      await load();
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function changeAccount() {
    setBusy("change");
    setNotice("");
    try {
      await apiRequest("/integrations/blotato/select-account", {
        method: "POST",
        body: JSON.stringify({ platform: "instagram", account_id: null }),
      });
      await load();
      flash(t("Выберите другой Instagram аккаунт."));
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
      await apiRequest("/integrations/blotato/disconnect", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setApiKey("");
      setIgAccount("");
      flash(t("Blotato отключён."));
      await load();
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

  const igName =
    blotato?.instagram?.account_name ||
    igAccounts.find((account) => account.id === blotato?.instagram?.account_id)
      ?.display_name ||
    t("Instagram аккаунт");

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
      {notice ? (
        <div className={`feedback feedback-${noticeKind === "error" ? "error" : "success"}`}>
          {notice}
        </div>
      ) : null}

      {/* --- Instagram через Blotato --------------------------------------- */}
      <section className="integration-card integration-card-wide">
        <div className="integration-card-head">
          <h2>{t("Instagram через Blotato")}</h2>
          <Status value={igState === "c" ? "active" : "disabled"}>
            {igState === "c"
              ? t("Instagram подключён")
              : igState === "b"
                ? t("Выберите аккаунт")
                : t("Не подключено")}
          </Status>
        </div>

        {igState === "a" ? (
          <div className="integration-block">
            <h3>{t("Подключите Blotato для автопостинга")}</h3>
            <p className="muted">
              {t("Growly будет отправлять готовые посты в Blotato, а Blotato опубликует их в Instagram.")}
            </p>
            <label className="full">
              <span>{t("API-ключ Blotato")}</span>
              <input
                autoComplete="off"
                onChange={(event) => setApiKey(event.target.value)}
                placeholder={t("Вставьте BLOTATO_API_KEY")}
                type="password"
                value={apiKey}
              />
            </label>
            <p className="muted plan-note-muted">
              {t("Ключ хранится только на сервере в зашифрованном виде и никогда не возвращается в браузер.")}
            </p>
            <div className="integration-actions">
              <button
                className="button button-primary"
                disabled={busy !== ""}
                onClick={saveApiKey}
                type="button"
              >
                {busy === "connect" ? t("Проверяем") : t("Сохранить API ключ")}
              </button>
            </div>
          </div>
        ) : null}

        {igState === "b" ? (
          <div className="integration-block">
            <p className="muted">
              {t("Blotato подключён. Выберите Instagram аккаунт для автопостинга.")}
            </p>
            {igAccounts.length === 0 ? (
              <p className="plan-note plan-note-muted">
                {t("Instagram аккаунты не найдены. Сначала подключите Instagram в кабинете Blotato, затем вернитесь сюда и нажмите «Обновить аккаунты».")}
              </p>
            ) : (
              <label className="full">
                <span>{t("Instagram аккаунт")}</span>
                <select
                  onChange={(event) => setIgAccount(event.target.value)}
                  value={igAccount}
                >
                  <option value="">{t("Выберите аккаунт")}</option>
                  {igAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.display_name || account.name || account.id}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <div className="integration-actions">
              <button
                className="button button-primary"
                disabled={busy !== "" || !igAccount}
                onClick={selectInstagram}
                type="button"
              >
                {busy === "select" ? t("Сохраняем") : t("Сохранить аккаунт")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={refreshAccounts}
                type="button"
              >
                {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
              </button>
              <a
                className="button button-secondary"
                href="https://my.blotato.com"
                rel="noreferrer"
                target="_blank"
              >
                {t("Открыть кабинет Blotato")}
              </a>
            </div>
          </div>
        ) : null}

        {igState === "c" ? (
          <div className="integration-block">
            <ul className="integration-facts">
              <li>
                {t("Аккаунт")}: <strong>{igName}</strong>
              </li>
              <li>
                {t("Аккаунтов в Blotato")}: <strong>{blotato?.accounts_count ?? 0}</strong>
              </li>
            </ul>
            <div className="integration-actions">
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={testConnection}
                type="button"
              >
                {busy === "test" ? t("Проверяем") : t("Проверить подключение")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={changeAccount}
                type="button"
              >
                {busy === "change" ? t("Готовим") : t("Сменить аккаунт")}
              </button>
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={disconnect}
                type="button"
              >
                {busy === "disconnect" ? t("Отключаем") : t("Отключить")}
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {/* --- Other channels ----------------------------------------------- */}
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
        </section>

        <section className="integration-card">
          <div className="integration-card-head">
            <h2>{t("Другие соцсети")}</h2>
            <Status value={blotato?.connected ? "active" : "disabled"}>
              {blotato?.connected ? t("Подключено") : t("Не подключено")}
            </Status>
          </div>
          <p className="muted">
            {t("Threads, TikTok, YouTube, Facebook, LinkedIn и X публикуются через Blotato.")}
          </p>
          <div className="integration-actions">
            <Link
              className="button button-secondary button-small"
              href="/settings/integrations/blotato"
            >
              {t("Настроить публикацию")}
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
