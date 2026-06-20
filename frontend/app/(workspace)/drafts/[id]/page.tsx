"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { FriendlyError } from "@/components/friendly-error";
import {
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import {
  apiErrorDebugInfo,
  apiRequest,
  formatDate,
  type ApiDebugInfo,
} from "@/lib/api";
import {
  PUBLISH_PLATFORMS,
  accountForPlatform,
  platformConnected,
  publishRequestBody,
  scheduleRequestBody,
  type BlotatoAccount,
  type IntegrationsStatus,
  type ManualPackage,
  type PublishResult,
} from "@/lib/integrations";
import { useLanguage } from "@/lib/i18n";
import type { Draft } from "@/lib/types";

type Mode = "now" | "schedule" | "manual";

export default function DraftDetailPage() {
  const params = useParams<{ id: string }>();
  const draftId = Number(params.id);
  const { locale, t } = useLanguage();

  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);

  const [selected, setSelected] = useState<string[]>([]);
  const [mode, setMode] = useState<Mode>("now");
  const [scheduledTime, setScheduledTime] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState<PublishResult | null>(null);
  const [packages, setPackages] = useState<ManualPackage[]>([]);
  const [actionError, setActionError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    try {
      const [draftResp, statusResp, accountsResp] = await Promise.all([
        apiRequest<{ draft: Draft }>(`/drafts/${draftId}`),
        apiRequest<IntegrationsStatus>("/integrations/status"),
        apiRequest<{ accounts: BlotatoAccount[] }>("/integrations/blotato/accounts"),
      ]);
      setDraft(draftResp.draft);
      setStatus(statusResp);
      setAccounts(accountsResp.accounts || []);
    } catch (value) {
      setFailed(true);
      setErrorDebug(apiErrorDebugInfo(value));
    } finally {
      setLoading(false);
    }
  }, [draftId]);

  useEffect(() => {
    void load();
  }, [load]);

  function toggle(slug: string) {
    setSelected((current) =>
      current.includes(slug)
        ? current.filter((item) => item !== slug)
        : [...current, slug],
    );
  }

  const draftEmpty = !draft || !draft.text || !draft.text.trim();

  async function publish() {
    if (draftEmpty || !selected.length) return;
    setPublishing(true);
    setActionError("");
    setResult(null);
    try {
      const body =
        mode === "schedule"
          ? scheduleRequestBody(selected, scheduledTime, [], locale)
          : publishRequestBody(selected, true, null, [], locale);
      const endpoint =
        mode === "schedule"
          ? `/drafts/${draftId}/schedule-blotato`
          : `/drafts/${draftId}/publish-blotato`;
      const response = await apiRequest<PublishResult>(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResult(response);
    } catch (value) {
      setActionError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
    } finally {
      setPublishing(false);
    }
  }

  async function makeManualPackage() {
    const platforms = selected.filter((slug) => slug !== "telegram");
    if (draftEmpty || !platforms.length) return;
    setPublishing(true);
    setActionError("");
    try {
      const response = await apiRequest<{ packages: ManualPackage[] }>(
        `/drafts/${draftId}/manual-package`,
        { method: "POST", body: JSON.stringify({ platforms, language: locale }) },
      );
      setPackages(response.packages || []);
    } catch (value) {
      setActionError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
    } finally {
      setPublishing(false);
    }
  }

  if (loading) {
    return (
      <div className="workspace-page">
        <LoadingState label={t("Загружаем черновик")} />
      </div>
    );
  }
  if (failed || !draft) {
    return (
      <div className="workspace-page">
        <FriendlyError debug={errorDebug} onRetry={load} />
      </div>
    );
  }

  const blotatoEnabled = Boolean(status?.blotato.enabled);

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Черновик")}
        title={draft.title || `${t("Черновик")} ${draft.id}`}
        description={`${draft.channel || t("Канал не указан")} · ${t("версия {version}", { version: draft.version })}`}
        action={
          <Link className="button button-secondary" href="/drafts">
            {t("Все черновики")}
          </Link>
        }
      />

      <div className="draft-detail">
        <article className="draft-detail-text">
          <div className="item-meta">
            <Status value={draft.status}>{draft.status}</Status>
            <span className="muted">{formatDate(draft.updated_at, locale)}</span>
          </div>
          <div className="draft-text">{draft.text}</div>
        </article>

        <section className="publishing-panel">
          <h2>{t("Публикация")}</h2>
          {!blotatoEnabled ? (
            <p className="plan-note plan-note-muted">
              {t("Blotato не подключён. Автопубликация в соцсети временно недоступна.")}
            </p>
          ) : null}

          <div className="platform-list">
            {PUBLISH_PLATFORMS.map((platform) => {
              const connected =
                platform.slug === "telegram"
                  ? Boolean(status?.telegram.connected)
                  : platformConnected(accounts, platform.slug);
              const account = accountForPlatform(accounts, platform.slug);
              return (
                <label className="platform-row" key={platform.slug}>
                  <input
                    checked={selected.includes(platform.slug)}
                    onChange={() => toggle(platform.slug)}
                    type="checkbox"
                  />
                  <span className="platform-name">{platform.label}</span>
                  <Status value={connected ? "active" : "disabled"}>
                    {connected ? t("Подключено") : t("Не подключено")}
                  </Status>
                  <span className="muted platform-account">
                    {platform.slug === "telegram"
                      ? t("Через Telegram-бота")
                      : account
                        ? account.display_name || account.name
                        : t("Нет аккаунта")}
                  </span>
                </label>
              );
            })}
          </div>

          <div className="publish-modes">
            <label>
              <input checked={mode === "now"} onChange={() => setMode("now")} name="mode" type="radio" />
              {t("Опубликовать сейчас")}
            </label>
            <label>
              <input checked={mode === "schedule"} onChange={() => setMode("schedule")} name="mode" type="radio" />
              {t("Запланировать")}
            </label>
            <label>
              <input checked={mode === "manual"} onChange={() => setMode("manual")} name="mode" type="radio" />
              {t("Пакет для ручной публикации")}
            </label>
          </div>

          {mode === "schedule" ? (
            <label className="schedule-input">
              <span>{t("Дата и время публикации")}</span>
              <input
                onChange={(event) => setScheduledTime(event.target.value)}
                type="datetime-local"
                value={scheduledTime}
              />
            </label>
          ) : null}

          {draftEmpty ? (
            <p className="plan-note plan-note-muted">
              {t("Черновик пуст — публикация недоступна.")}
            </p>
          ) : null}
          {actionError ? <FriendlyError message={actionError} /> : null}

          <div className="form-actions">
            {mode === "manual" ? (
              <button
                className="button button-primary"
                disabled={publishing || draftEmpty || !selected.length}
                onClick={makeManualPackage}
                type="button"
              >
                <Icon name="draft" />
                {publishing ? t("Готовим") : t("Подготовить пакет для ручной публикации")}
              </button>
            ) : (
              <button
                className="button button-primary"
                disabled={
                  publishing ||
                  draftEmpty ||
                  !selected.length ||
                  (mode === "schedule" && !scheduledTime)
                }
                onClick={publish}
                type="button"
              >
                <Icon name={publishing ? "sync" : "arrow"} />
                {publishing
                  ? t("Отправляем")
                  : mode === "schedule"
                    ? t("Запланировать")
                    : t("Опубликовать сейчас")}
              </button>
            )}
          </div>

          {result ? (
            <div className="publish-results">
              {result.blotato_submissions.map((submission) => (
                <div className="publish-result-row" key={submission.platform}>
                  <strong>{submission.platform}</strong>
                  <Status value={submission.status === "failed" ? "failed" : "active"}>
                    {t(submissionLabel(submission.status))}
                  </Status>
                  {submission.url ? (
                    <a href={submission.url} rel="noreferrer" target="_blank">
                      {t("Открыть пост")}
                      <Icon name="external" />
                    </a>
                  ) : null}
                  {submission.error ? (
                    <span className="muted">{t(submission.error)}</span>
                  ) : null}
                </div>
              ))}
              {result.blotato_submissions.some((s) => s.status === "failed") ? (
                <button
                  className="button button-secondary button-small"
                  disabled={publishing}
                  onClick={publish}
                  type="button"
                >
                  {t("Повторить")}
                </button>
              ) : null}
            </div>
          ) : null}

          {packages.length ? (
            <div className="manual-packages">
              {packages.map((pkg) => (
                <article className="manual-package" key={pkg.platform}>
                  <h3>{pkg.platform}</h3>
                  {pkg.hook ? (
                    <p>
                      <strong>{t("Хук")}:</strong> {pkg.hook}
                    </p>
                  ) : null}
                  {pkg.caption ? (
                    <p>
                      <strong>{t("Текст")}:</strong> {pkg.caption}
                    </p>
                  ) : null}
                  {pkg.script ? (
                    <p>
                      <strong>{t("Сценарий")}:</strong> {pkg.script}
                    </p>
                  ) : null}
                  {pkg.visual_brief ? (
                    <p>
                      <strong>{t("Визуал")}:</strong> {pkg.visual_brief}
                    </p>
                  ) : null}
                  {pkg.hashtags ? (
                    <p>
                      <strong>{t("Хэштеги")}:</strong> {pkg.hashtags}
                    </p>
                  ) : null}
                  {pkg.cta ? (
                    <p>
                      <strong>CTA:</strong> {pkg.cta}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function submissionLabel(status: string): string {
  if (status === "submitted") return "Отправлено";
  if (status === "scheduled") return "Запланировано";
  if (status === "failed") return "Ошибка";
  if (status === "skipped") return "Пропущено";
  if (status === "unsupported") return "Не поддерживается";
  return status;
}
