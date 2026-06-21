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
} from "@/lib/integrations";
import { useLanguage } from "@/lib/i18n";

const CHECKLIST = [
  "Сохраните API-ключ Blotato на странице «Интеграции»",
  "Подключите аккаунты в Blotato",
  "Обновите аккаунты в Growly",
  "Сопоставьте аккаунты с платформами",
  "Проверьте публикацию",
];

export default function BlotatoSetupPage() {
  const { t } = useLanguage();
  const [status, setStatus] = useState<BlotatoStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

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
      const map: Record<string, string> = {};
      for (const mapping of mappingsResp.mappings || []) {
        if (mapping.account_id) map[mapping.platform] = mapping.account_id;
      }
      setMappings(map);
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

  async function saveMappings() {
    setBusy("save");
    setNotice("");
    try {
      const payload = Object.entries(mappings)
        .filter(([, accountId]) => accountId)
        .map(([platform, account_id]) => ({ platform, account_id }));
      await apiRequest("/integrations/blotato/mappings", {
        method: "POST",
        body: JSON.stringify({ mappings: payload }),
      });
      setNotice(t("Сопоставление аккаунтов сохранено."));
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
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
        eyebrow={t("Администрирование")}
        title={t("Настройка публикации")}
        description={t("Сопоставьте аккаунты Blotato с платформами Growly.")}
        action={
          <Link className="button button-secondary" href="/settings/integrations">
            {t("Назад к интеграциям")}
          </Link>
        }
      />

      {failed ? <FriendlyError debug={errorDebug} onRetry={load} /> : null}
      {notice ? <div className="feedback feedback-success">{notice}</div> : null}

      <section className="form-panel">
        <h2>{t("Чек-лист подключения")}</h2>
        <ol className="setup-checklist">
          {CHECKLIST.map((step, index) => (
            <li key={step}>
              <span className="setup-step-index">{index + 1}</span>
              {t(step)}
            </li>
          ))}
        </ol>
        <p className="muted">
          {t("API-ключ хранится только в секретах бэкенда и не отображается в интерфейсе.")}
        </p>
      </section>

      <section className="form-panel">
        <div className="section-heading">
          <h2>{t("Сопоставление платформ")}</h2>
          <button
            className="button button-secondary button-small"
            disabled={busy !== ""}
            onClick={refreshAccounts}
            type="button"
          >
            {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
          </button>
        </div>
        {accounts.length === 0 ? (
          <p className="plan-note plan-note-muted">
            {status?.enabled
              ? t("Аккаунты не найдены. Подключите их в Blotato и обновите список.")
              : t("Blotato не подключён. Автопубликация в соцсети временно недоступна.")}
          </p>
        ) : null}
        <div className="mapping-list">
          {BLOTATO_PLATFORMS.map((platform) => {
            const options = accountsByPlatform[platform.slug] || [];
            return (
              <label className="mapping-row" key={platform.slug}>
                <span className="mapping-platform">
                  {platform.label}
                  <Status value={options.length ? "active" : "disabled"}>
                    {options.length ? t("Подключено") : t("Не подключено")}
                  </Status>
                </span>
                <select
                  onChange={(event) =>
                    setMappings((current) => ({
                      ...current,
                      [platform.slug]: event.target.value,
                    }))
                  }
                  value={mappings[platform.slug] || ""}
                >
                  <option value="">{t("Не публиковать")}</option>
                  {options.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.display_name || account.name || account.id}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
        </div>
        <div className="form-actions">
          <button
            className="button button-primary"
            disabled={busy !== ""}
            onClick={saveMappings}
            type="button"
          >
            {busy === "save" ? t("Сохраняем") : t("Сохранить сопоставление")}
          </button>
        </div>
      </section>
    </div>
  );
}
