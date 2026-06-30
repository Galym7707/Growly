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

function accountName(account: BlotatoAccount | null): string {
  return account?.display_name || account?.name || account?.id || "—";
}

export default function IntegrationsPage() {
  const { t } = useLanguage();
  const [status, setStatus] = useState<BlotatoStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [mappings, setMappings] = useState<BlotatoMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);

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
      setMappings(mappingsResp.mappings || []);
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

  const mappingByPlatform = useMemo(() => {
    const index: Record<string, BlotatoMapping> = {};
    for (const mapping of mappings) index[mapping.platform] = mapping;
    return index;
  }, [mappings]);

  const accountById = useMemo(() => {
    const index: Record<string, BlotatoAccount> = {};
    for (const account of accounts) index[account.id] = account;
    return index;
  }, [accounts]);

  const connectedPlatforms = BLOTATO_PLATFORMS.filter(
    (platform) => accounts.some((account) => account.platform === platform.slug && account.connected),
  ).length;
  const readyPlatforms = BLOTATO_PLATFORMS.filter((platform) => {
    const mapping = mappingByPlatform[platform.slug];
    if (!mapping?.account_id) return false;
    if ((platform.requiresPage || platform.requiresBoard) && !mapping.page_id) return false;
    return true;
  }).length;

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
        eyebrow={t("Конфигурация")}
        title={t("Интеграции")}
        description={t("Подключите аккаунты Blotato и выберите, куда Growly будет публиковать посты.")}
        action={
          <Link className="button button-secondary" href="/settings">
            {t("Назад к настройкам")}
          </Link>
        }
      />

      {failed ? <FriendlyError debug={errorDebug} onRetry={load} /> : null}

      <section className="integration-card integration-card-wide integration-overview">
        <div className="integration-card-head">
          <div>
            <p className="eyebrow">{t("Growly → Blotato → соцсети")}</p>
            <h2>{t("Автопостинг через Blotato")}</h2>
          </div>
          <Status value={status?.enabled ? "active" : "disabled"}>
            {status?.enabled ? t("Подключено") : t("Не подключено")}
          </Status>
        </div>
        <p className="muted">
          {t("Пользователь подключает свой Blotato API key, Growly подтягивает доступные соцсети и сохраняет выбранные аккаунты только для текущего workspace. Пароли соцсетей не запрашиваются и не хранятся.")}
        </p>
        <div className="integration-metrics">
          <div>
            <span>{t("Аккаунтов найдено")}</span>
            <strong>{accounts.length}</strong>
          </div>
          <div>
            <span>{t("Платформ с аккаунтами")}</span>
            <strong>{connectedPlatforms}</strong>
          </div>
          <div>
            <span>{t("Готово к публикации")}</span>
            <strong>{readyPlatforms}</strong>
          </div>
        </div>
        <div className="integration-actions">
          <Link className="button button-primary" href="/settings/integrations/blotato">
            {status?.enabled ? t("Настроить аккаунты") : t("Подключить Blotato")}
          </Link>
          <button className="button button-secondary" onClick={load} type="button">
            {t("Обновить статус")}
          </button>
        </div>
      </section>

      <section className="form-panel">
        <div className="section-heading">
          <h2>{t("Соцсети")}</h2>
          <p className="muted">{t("Показываем все платформы, которые Growly умеет публиковать через Blotato.")}</p>
        </div>
        <div className="platform-matrix">
          {BLOTATO_PLATFORMS.map((platform) => {
            const mapping = mappingByPlatform[platform.slug];
            const mappedAccount = mapping?.account_id ? accountById[mapping.account_id] || null : null;
            const platformAccounts = accounts.filter(
              (account) => account.platform === platform.slug && account.connected,
            );
            const ready = Boolean(
              mapping?.account_id &&
                (!(platform.requiresPage || platform.requiresBoard) || mapping.page_id),
            );
            return (
              <div className="platform-row" key={platform.slug}>
                <div>
                  <strong>{platform.label}</strong>
                  <span>
                    {ready
                      ? accountName(mappedAccount)
                      : platformAccounts.length
                        ? t("Аккаунт найден, выберите его в настройках")
                        : t("Аккаунт не найден")}
                  </span>
                </div>
                <Status value={ready ? "active" : platformAccounts.length ? "pending" : "disabled"}>
                  {ready
                    ? t("Готово")
                    : platformAccounts.length
                      ? t("Нужно выбрать")
                      : t("Нет аккаунта")}
                </Status>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
