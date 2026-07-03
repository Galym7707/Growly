"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FriendlyError } from "@/components/friendly-error";
import { LoadingState, PageHeader, Status } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import {
  BLOTATO_PLATFORMS,
  type BlotatoAccount,
  type BlotatoMapping,
  type BlotatoStatus,
  type PlatformMeta,
} from "@/lib/integrations";
import { useLanguage } from "@/lib/i18n";

type MappingDraft = {
  account_id: string;
  page_id: string;
};

type ConnectResponse = {
  status: BlotatoStatus;
  accounts: BlotatoAccount[];
};

const STEPS = [
  "Откройте Blotato и подключите нужные соцсети там.",
  "Скопируйте API key Blotato и вставьте его в Growly.",
  "Обновите аккаунты и выберите аккаунт для каждой платформы.",
  "Для Facebook выберите страницу, для Pinterest укажите Board ID.",
];

const SHARED_STEPS = [
  "Нажмите «Запросить подключение» у нужной платформы и укажите логин аккаунта.",
  "Команда Growly подключит аккаунт — обычно в течение рабочего дня.",
  "Когда аккаунт появится в списке, выберите его и сохраните настройки.",
];

function emptyMapping(): MappingDraft {
  return { account_id: "", page_id: "" };
}

function accountTitle(account: BlotatoAccount): string {
  return account.display_name || account.name || account.id;
}

function errorMessage(value: unknown, fallback: string): string {
  return value instanceof Error ? value.message : fallback;
}

export default function BlotatoSetupPage() {
  const { t } = useLanguage();
  const [status, setStatus] = useState<BlotatoStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [mappings, setMappings] = useState<Record<string, MappingDraft>>({});
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeKind, setNoticeKind] = useState<"success" | "error">("success");
  const [requestUsernames, setRequestUsernames] = useState<Record<string, string>>({});
  const [requestedPlatforms, setRequestedPlatforms] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    try {
      const [statusResp, accountsResp, mappingsResp] = await Promise.all([
        apiRequest<BlotatoStatus>("/integrations/blotato/status"),
        apiRequest<{ accounts: BlotatoAccount[] }>("/integrations/blotato/accounts"),
        apiRequest<{ mappings: BlotatoMapping[] }>("/integrations/blotato/mappings"),
      ]);
      setStatus(statusResp);
      setAccounts(accountsResp.accounts || []);
      const nextMappings: Record<string, MappingDraft> = {};
      for (const mapping of mappingsResp.mappings || []) {
        nextMappings[mapping.platform] = {
          account_id: mapping.account_id || "",
          page_id: mapping.page_id || "",
        };
      }
      setMappings(nextMappings);
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

  const accountsByPlatform = useMemo(() => {
    const grouped: Record<string, BlotatoAccount[]> = {};
    for (const account of accounts) {
      (grouped[account.platform] ||= []).push(account);
    }
    return grouped;
  }, [accounts]);

  const platforms = useMemo<PlatformMeta[]>(() => {
    const known = new Set(BLOTATO_PLATFORMS.map((platform) => platform.slug));
    const dynamic = Array.from(new Set(accounts.map((account) => account.platform)))
      .filter((platform) => platform && !known.has(platform))
      .map((platform) => ({
        slug: platform,
        label: platform,
        provider: "blotato" as const,
      }));
    return [...BLOTATO_PLATFORMS, ...dynamic];
  }, [accounts]);

  const readyCount = platforms.filter((platform) => platformReady(platform)).length;
  const shared = Boolean(status?.shared_key_active);

  function flash(message: string, kind: "success" | "error" = "success") {
    setNotice(message);
    setNoticeKind(kind);
  }

  function selectedMapping(platform: string): MappingDraft {
    return mappings[platform] || emptyMapping();
  }

  function selectedAccount(platform: string): BlotatoAccount | null {
    const mapping = selectedMapping(platform);
    return accounts.find((account) => account.id === mapping.account_id) || null;
  }

  function platformReady(platform: PlatformMeta): boolean {
    const mapping = selectedMapping(platform.slug);
    if (!mapping.account_id) return false;
    if ((platform.requiresPage || platform.requiresBoard) && !mapping.page_id) return false;
    return true;
  }

  function updateMapping(platform: string, patch: Partial<MappingDraft>) {
    setMappings((current) => {
      const previous = current[platform] || emptyMapping();
      return {
        ...current,
        [platform]: { ...previous, ...patch },
      };
    });
  }

  async function connect() {
    if (!apiKey.trim()) {
      flash(t("Вставьте API key Blotato."), "error");
      return;
    }
    setBusy("connect");
    setNotice("");
    try {
      const response = await apiRequest<ConnectResponse>("/integrations/blotato/connect", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });
      setApiKey("");
      setStatus(response.status);
      setAccounts(response.accounts || []);
      await load();
      flash(t("Blotato подключён. Аккаунты обновлены."));
    } catch (value) {
      flash(errorMessage(value, t("Не удалось подключить Blotato.")), "error");
    } finally {
      setBusy("");
    }
  }

  async function disconnect() {
    setBusy("disconnect");
    setNotice("");
    try {
      await apiRequest("/integrations/blotato/connect", { method: "DELETE" });
      setAccounts([]);
      setMappings({});
      await load();
      flash(t("Blotato отключён."));
    } catch (value) {
      flash(errorMessage(value, t("Не удалось отключить Blotato.")), "error");
    } finally {
      setBusy("");
    }
  }

  async function refreshAccounts() {
    setBusy("accounts");
    setNotice("");
    try {
      const response = await apiRequest<{ accounts: BlotatoAccount[] }>(
        "/integrations/blotato/accounts?refresh=true",
      );
      setAccounts(response.accounts || []);
      await load();
      flash(t("Список аккаунтов обновлён."));
    } catch (value) {
      flash(errorMessage(value, t("Не удалось обновить аккаунты.")), "error");
    } finally {
      setBusy("");
    }
  }

  async function requestConnection(platform: string) {
    setBusy(`request-${platform}`);
    setNotice("");
    try {
      await apiRequest("/integrations/social/request", {
        method: "POST",
        body: JSON.stringify({
          platform,
          username: (requestUsernames[platform] || "").trim() || null,
        }),
      });
      setRequestedPlatforms((current) => ({ ...current, [platform]: true }));
      flash(
        t("Заявка отправлена. Мы подключим аккаунт, и он появится в этом списке."),
      );
    } catch (value) {
      flash(errorMessage(value, t("Не удалось отправить заявку.")), "error");
    } finally {
      setBusy("");
    }
  }

  async function saveMappings() {
    setBusy("save");
    setNotice("");
    try {
      const payload = Object.entries(mappings).map(([platform, mapping]) => ({
        platform,
        account_id: mapping.account_id || null,
        page_id: mapping.page_id || null,
      }));
      await apiRequest("/integrations/blotato/mappings", {
        method: "POST",
        body: JSON.stringify({ mappings: payload }),
      });
      await load();
      flash(t("Аккаунты для публикации сохранены."));
    } catch (value) {
      flash(errorMessage(value, t("Не удалось сохранить настройки.")), "error");
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

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Соцсети")}
        title={t("Подключение Blotato")}
        description={t("Настройте аккаунты, которые Growly будет использовать для публикации в соцсети.")}
        action={
          <Link className="button button-secondary" href="/settings/integrations">
            {t("Назад к интеграциям")}
          </Link>
        }
      />

      {failed ? <FriendlyError debug={errorDebug} onRetry={load} /> : null}
      {notice ? (
        <div className={`feedback feedback-${noticeKind === "error" ? "error" : "success"}`}>
          {notice}
        </div>
      ) : null}

      {shared ? (
        <section className="integration-card integration-card-wide">
          <div className="integration-card-head">
            <div>
              <p className="eyebrow">{t("Публикация")}</p>
              <h2>{t("Публикация включена через Growly")}</h2>
            </div>
            <Status value="active">{t("Подключено")}</Status>
          </div>
          <p className="muted">
            {t("Свой ключ и сторонние сервисы не нужны: Growly публикует через собственную подписку. Просто запросите подключение нужных аккаунтов ниже.")}
          </p>
        </section>
      ) : (
        <section className="integration-card integration-card-wide">
          <div className="integration-card-head">
            <div>
              <p className="eyebrow">{t("Шаг 1")}</p>
              <h2>{t("Ключ Blotato")}</h2>
            </div>
            <Status value={status?.enabled ? "active" : "disabled"}>
              {status?.enabled ? t("Ключ сохранён") : t("Ключ не сохранён")}
            </Status>
          </div>
          <p className="muted">
            {t("Ключ нужен только backend-части Growly. Мы сохраняем его зашифрованным и никогда не показываем обратно в интерфейсе.")}
          </p>
          <div className="secret-connect-row">
            <label>
              <span>{t("Blotato API key")}</span>
              <input
                autoComplete="off"
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="blotato_..."
                type="password"
                value={apiKey}
              />
            </label>
            <button
              className="button button-primary"
              disabled={busy !== ""}
              onClick={connect}
              type="button"
            >
              {busy === "connect" ? t("Проверяем") : status?.enabled ? t("Заменить ключ") : t("Подключить")}
            </button>
            {status?.enabled ? (
              <button
                className="button button-secondary"
                disabled={busy !== ""}
                onClick={disconnect}
                type="button"
              >
                {busy === "disconnect" ? t("Отключаем") : t("Отключить")}
              </button>
            ) : null}
          </div>
        </section>
      )}

      <section className="form-panel">
        <div className="section-heading">
          <h2>{t("Как подключить соцсети")}</h2>
          <p className="muted">
            {shared
              ? t("Опишите, какие аккаунты нужны, — команда Growly подключит их за вас.")
              : t("Growly работает с теми аккаунтами, которые уже подключены внутри Blotato.")}
          </p>
        </div>
        <ol className="setup-checklist">
          {(shared ? SHARED_STEPS : STEPS).map((step, index) => (
            <li key={step}>
              <span className="setup-step-index">{index + 1}</span>
              {t(step)}
            </li>
          ))}
        </ol>
      </section>

      <section className="form-panel">
        <div className="section-heading">
          <div>
            <h2>{t("Аккаунты для публикации")}</h2>
            <p className="muted">
              {t("Найдено аккаунтов: {count}. Готово к публикации: {ready}.", {
                count: accounts.length,
                ready: readyCount,
              })}
            </p>
          </div>
          <button
            className="button button-secondary button-small"
            disabled={busy !== "" || !status?.enabled}
            onClick={refreshAccounts}
            type="button"
          >
            {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
          </button>
        </div>

        {!status?.enabled ? (
          <p className="plan-note plan-note-muted">
            {t("Сначала подключите Blotato API key. После проверки Growly покажет доступные аккаунты.")}
          </p>
        ) : null}
        {status?.enabled && accounts.length === 0 ? (
          <p className="plan-note plan-note-muted">
            {shared
              ? t("Аккаунты ещё не подключены. Запросите подключение нужной платформы ниже — это бесплатно и не требует регистрации в сторонних сервисах.")
              : t("Аккаунты не найдены. Подключите соцсети в Blotato и нажмите «Обновить аккаунты».")}
          </p>
        ) : null}

        <div className="mapping-list mapping-list-expanded">
          {platforms.map((platform) => {
            const options = accountsByPlatform[platform.slug] || [];
            const mapping = selectedMapping(platform.slug);
            const account = selectedAccount(platform.slug);
            const subaccounts = account?.subaccounts || [];
            const ready = platformReady(platform);
            return (
              <div className="mapping-row mapping-row-expanded" key={platform.slug}>
                <div className="mapping-platform">
                  <strong>{platform.label}</strong>
                  <Status value={ready ? "active" : options.length ? "pending" : "disabled"}>
                    {ready ? t("Готово") : options.length ? t("Нужно выбрать") : t("Нет аккаунта")}
                  </Status>
                  {platform.helper ? <span className="mapping-helper">{platform.helper}</span> : null}
                </div>

                <div className="mapping-controls">
                  <label>
                    <span>{t("Аккаунт")}</span>
                    <select
                      disabled={!options.length}
                      onChange={(event) =>
                        updateMapping(platform.slug, {
                          account_id: event.target.value,
                          page_id: "",
                        })
                      }
                      value={mapping.account_id}
                    >
                      <option value="">{t("Не публиковать")}</option>
                      {options.map((option) => (
                        <option key={option.id} value={option.id}>
                          {accountTitle(option)}
                        </option>
                      ))}
                    </select>
                  </label>

                  {platform.requiresPage || subaccounts.length ? (
                    <label>
                      <span>{platform.requiresPage ? t("Страница") : t("Страница / компания")}</span>
                      <select
                        disabled={!mapping.account_id || !subaccounts.length}
                        onChange={(event) =>
                          updateMapping(platform.slug, { page_id: event.target.value })
                        }
                        value={mapping.page_id}
                      >
                        <option value="">
                          {subaccounts.length ? t("Выберите страницу") : t("Страницы не найдены")}
                        </option>
                        {subaccounts.map((subaccount) => (
                          <option key={subaccount.id} value={subaccount.id}>
                            {subaccount.name || subaccount.id}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}

                  {platform.requiresBoard ? (
                    <label>
                      <span>{t("Pinterest Board ID")}</span>
                      <input
                        disabled={!mapping.account_id}
                        onChange={(event) =>
                          updateMapping(platform.slug, { page_id: event.target.value })
                        }
                        placeholder="board_id"
                        value={mapping.page_id}
                      />
                    </label>
                  ) : null}

                  {shared && !options.length ? (
                    requestedPlatforms[platform.slug] ? (
                      <p className="mapping-helper">
                        {t("Заявка отправлена. Аккаунт появится здесь после подключения.")}
                      </p>
                    ) : (
                      <div className="secret-connect-row">
                        <label>
                          <span>{t("Логин или ссылка на аккаунт")}</span>
                          <input
                            onChange={(event) =>
                              setRequestUsernames((current) => ({
                                ...current,
                                [platform.slug]: event.target.value,
                              }))
                            }
                            placeholder="@username"
                            value={requestUsernames[platform.slug] || ""}
                          />
                        </label>
                        <button
                          className="button button-secondary"
                          disabled={busy !== ""}
                          onClick={() => requestConnection(platform.slug)}
                          type="button"
                        >
                          {busy === `request-${platform.slug}`
                            ? t("Отправляем")
                            : t("Запросить подключение")}
                        </button>
                      </div>
                    )
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        <div className="form-actions">
          <button
            className="button button-primary"
            disabled={busy !== "" || !status?.enabled}
            onClick={saveMappings}
            type="button"
          >
            {busy === "save" ? t("Сохраняем") : t("Сохранить настройки публикации")}
          </button>
        </div>
      </section>
    </div>
  );
}
