"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "@/components/icons";
import { FriendlyError } from "@/components/friendly-error";
import { Status } from "@/components/ui";
import { ToastStack, useToasts } from "@/components/toast";
import { DraftHeader } from "@/components/draft/draft-header";
import { DraftTextCard } from "@/components/draft/draft-text-card";
import { DraftPreviewCard } from "@/components/draft/draft-preview-card";
import {
  ChannelSelector,
  type ChannelDescriptor,
} from "@/components/draft/channel-selector";
import {
  PublicationModeSelector,
  type PublishMode,
} from "@/components/draft/publication-mode-selector";
import { MediaGrid } from "@/components/draft/media-grid";
import { MediaGeneratorPanel } from "@/components/draft/media-generator-panel";
import { StickyPublishActions } from "@/components/draft/sticky-publish-actions";
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
import {
  MEDIA_ACCEPT,
  isAllowedMediaFile,
  mediaKind,
  mergeMedia,
  visualStatusLabel,
  type AttachedMedia,
} from "@/lib/media";
import type { Draft } from "@/lib/types";

type VisualKind = "image" | "video";

type MediaUploadTicket = {
  presigned_url: string;
  public_url: string;
};

type VisualResult = {
  id: string | null;
  status: string;
  media_urls: string[];
};

const MAX_MEDIA_ITEMS = 10;
const VISUAL_POLL_INTERVAL_MS = 5_000;
const VISUAL_POLL_ATTEMPTS = 120;

export default function DraftDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const intent = searchParams.get("intent");
  const draftId = Number(params.id);
  const { locale, t } = useLanguage();
  const { toasts, push: pushToast, dismiss: dismissToast } = useToasts();

  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);

  const [selected, setSelected] = useState<string[]>([]);
  const [mode, setMode] = useState<PublishMode>(
    intent === "schedule" ? "schedule" : "now",
  );
  const [scheduledTime, setScheduledTime] = useState("");
  const [manualMediaUrl, setManualMediaUrl] = useState("");
  const [attachedMedia, setAttachedMedia] = useState<AttachedMedia[]>([]);
  const [uploading, setUploading] = useState(false);
  const [visualKind, setVisualKind] = useState<VisualKind>("image");
  const [visualPrompt, setVisualPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState("");
  const mediaInputRef = useRef<HTMLInputElement>(null);
  // Tracks the active generation so the user can abort a stuck Blotato poll
  // instead of waiting out the full timeout with the UI locked.
  const generationRef = useRef<{
    cancelled: boolean;
    timer: number | null;
    resolveSleep: (() => void) | null;
    controller: AbortController;
  } | null>(null);
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
      setVisualPrompt((current) =>
        current ||
        `Создай визуал для публикации «${draftResp.draft.title || `Черновик ${draftResp.draft.id}`}». ${draftResp.draft.text.slice(0, 3000)}`,
      );
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

  // Abort any in-flight visual generation if the user leaves the page so the
  // poll loop doesn't keep running (and updating state) after unmount.
  useEffect(() => {
    return () => {
      const token = generationRef.current;
      if (token) {
        token.cancelled = true;
        if (token.timer !== null) window.clearTimeout(token.timer);
        token.resolveSleep?.();
        token.controller.abort();
      }
    };
  }, []);

  // When opened from the content plan (with an intent), preselect the platform
  // that matches the draft's channel so the user lands ready to publish.
  useEffect(() => {
    if (!draft || !intent || selected.length) return;
    const channel = (draft.channel || "").toLowerCase();
    const match = PUBLISH_PLATFORMS.find((platform) =>
      channel.includes(platform.slug),
    );
    if (match) setSelected([match.slug]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, intent]);

  function toggle(slug: string) {
    setSelected((current) =>
      current.includes(slug)
        ? current.filter((item) => item !== slug)
        : [...current, slug],
    );
  }

  function removeMedia(url: string) {
    setAttachedMedia((current) => current.filter((media) => media.url !== url));
  }

  const draftEmpty = !draft || !draft.text || !draft.text.trim();
  const mediaUrls = useMemo(
    () =>
      Array.from(
        new Set([
          ...attachedMedia.map((item) => item.url),
          ...(manualMediaUrl.trim() ? [manualMediaUrl.trim()] : []),
        ]),
      ),
    [attachedMedia, manualMediaUrl],
  );
  // Instagram requires at least one image or video to publish.
  const instagramNeedsMedia =
    selected.includes("instagram") && mediaUrls.length === 0;
  const blotatoEnabled = Boolean(status?.blotato.enabled);

  // Channel descriptors split connected / disconnected for the selector.
  const channels: ChannelDescriptor[] = useMemo(
    () =>
      PUBLISH_PLATFORMS.map((platform) => {
        const connected =
          platform.slug === "telegram"
            ? Boolean(status?.telegram.connected)
            : platformConnected(accounts, platform.slug);
        const account = accountForPlatform(accounts, platform.slug);
        const accountLabel =
          platform.slug === "telegram"
            ? t("Через Telegram-бота")
            : account
              ? account.display_name || account.name
              : t("Нет аккаунта");
        return { slug: platform.slug, label: platform.label, connected, accountLabel };
      }),
    [accounts, status, t],
  );

  const instagramUsername = useMemo(() => {
    const account = accountForPlatform(accounts, "instagram");
    return account ? account.display_name || account.name : null;
  }, [accounts]);

  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return;
    const availableSlots = MAX_MEDIA_ITEMS - attachedMedia.length;
    if (availableSlots <= 0) {
      setActionError(t("Можно добавить не более 10 файлов."));
      return;
    }
    const selectedFiles = Array.from(files).slice(0, availableSlots);
    const unsupported = selectedFiles.find((file) => !isAllowedMediaFile(file));
    if (unsupported) {
      setActionError(
        t("Поддерживаются изображения JPG, PNG, WEBP, GIF и видео MP4, MOV, WEBM."),
      );
      return;
    }
    setUploading(true);
    setActionError("");
    try {
      for (const file of selectedFiles) {
        const ticket = await apiRequest<MediaUploadTicket>(
          "/integrations/blotato/media-upload",
          {
            method: "POST",
            body: JSON.stringify({ filename: file.name }),
          },
        );
        const response = await fetch(ticket.presigned_url, {
          method: "PUT",
          headers: {
            "Content-Type": file.type || "application/octet-stream",
          },
          body: file,
        });
        if (!response.ok) {
          throw new Error(t("Не удалось загрузить файл в Blotato."));
        }
        setAttachedMedia((current) =>
          mergeMedia(current, [
            {
              url: ticket.public_url,
              kind: mediaKind(file.name, file.type),
              name: file.name,
            },
          ]),
        );
      }
    } catch (value) {
      setActionError(
        value instanceof Error
          ? t(value.message)
          : t("Не удалось загрузить файл в Blotato."),
      );
    } finally {
      setUploading(false);
      if (mediaInputRef.current) mediaInputRef.current.value = "";
    }
  }

  async function generateVisual() {
    const prompt = visualPrompt.trim();
    if (!prompt || generating) return;
    const token = {
      cancelled: false,
      timer: null as number | null,
      resolveSleep: null as (() => void) | null,
      controller: new AbortController(),
    };
    generationRef.current = token;
    setGenerating(true);
    setGenerationStatus(t("В очереди"));
    setActionError("");
    try {
      let visual = await apiRequest<VisualResult>(
        "/integrations/blotato/visuals",
        {
          method: "POST",
          body: JSON.stringify({
            kind: visualKind,
            prompt,
            title: draft?.title || null,
          }),
          signal: token.controller.signal,
        },
      );
      if (!visual.id) {
        throw new Error(t("Blotato не вернул ID созданного медиа."));
      }
      const visualId = visual.id;
      for (let attempt = 0; attempt < VISUAL_POLL_ATTEMPTS; attempt += 1) {
        if (token.cancelled) return;
        setGenerationStatus(t(visualStatusLabel(visual.status)));
        if (visual.status === "done") {
          if (!visual.media_urls.length) {
            throw new Error(t("Blotato не вернул созданное медиа."));
          }
          setAttachedMedia((current) =>
            mergeMedia(
              current,
              visual.media_urls.map((url, index) => ({
                url,
                kind: mediaKind(url),
                name: `${t(visualKind === "video" ? "AI-видео" : "AI-изображение")} ${index + 1}`,
              })),
            ),
          );
          setGenerationStatus(t("Медиа готово и добавлено к публикации."));
          pushToast("success", t("Медиа готово и добавлено к публикации."));
          return;
        }
        if (visual.status === "creation-from-template-failed") {
          throw new Error(t("Blotato не удалось сгенерировать медиа."));
        }
        // Cancellable wait: the cancel button clears this timer to abort early
        // instead of leaving the user stuck for the full poll interval.
        await new Promise<void>((resolve) => {
          token.resolveSleep = resolve;
          token.timer = window.setTimeout(resolve, VISUAL_POLL_INTERVAL_MS);
        });
        if (token.cancelled) return;
        visual = await apiRequest<VisualResult>(
          `/integrations/blotato/visuals/${encodeURIComponent(visualId)}`,
          { signal: token.controller.signal },
        );
      }
      throw new Error(
        t("Генерация заняла слишком много времени. Проверьте результат в Blotato."),
      );
    } catch (value) {
      // A user-triggered cancel aborts the in-flight request; that is expected,
      // so don't surface it as an error.
      if (token.cancelled) return;
      setGenerationStatus("");
      const message =
        value instanceof Error
          ? t(value.message)
          : t("Blotato не удалось сгенерировать медиа.");
      setActionError(message);
      pushToast("error", message);
    } finally {
      if (generationRef.current === token) generationRef.current = null;
      if (!token.cancelled) setGenerating(false);
    }
  }

  function cancelGeneration() {
    const token = generationRef.current;
    if (token) {
      token.cancelled = true;
      if (token.timer !== null) window.clearTimeout(token.timer);
      token.resolveSleep?.();
      token.controller.abort();
      generationRef.current = null;
    }
    setGenerating(false);
    setGenerationStatus("");
  }

  async function publish() {
    if (draftEmpty || !selected.length || instagramNeedsMedia) return;
    setPublishing(true);
    setActionError("");
    setResult(null);
    try {
      const body =
        mode === "schedule"
          ? scheduleRequestBody(selected, scheduledTime, mediaUrls, locale)
          : publishRequestBody(selected, true, null, mediaUrls, locale);
      const endpoint =
        mode === "schedule"
          ? `/drafts/${draftId}/schedule-blotato`
          : `/drafts/${draftId}/publish-blotato`;
      const response = await apiRequest<PublishResult>(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResult(response);
      const anyFailed = response.blotato_submissions.some(
        (submission) => submission.status === "failed",
      );
      if (anyFailed) {
        const firstError = response.blotato_submissions.find(
          (submission) => submission.status === "failed" && submission.error,
        )?.error;
        pushToast(
          "error",
          firstError ? t(firstError) : t("Не удалось опубликовать"),
        );
      } else {
        pushToast(
          "success",
          mode === "schedule" ? t("Пост запланирован") : t("Пост опубликован"),
        );
      }
    } catch (value) {
      const message =
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
      setActionError(message);
      pushToast("error", message);
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
      pushToast("success", t("Пакет готов"));
    } catch (value) {
      const message =
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
      setActionError(message);
      pushToast("error", t("Не удалось подготовить пакет"));
    } finally {
      setPublishing(false);
    }
  }

  if (loading) {
    return (
      <div className="draft-page">
        <div className="draft-skeleton">
          <div className="skeleton skeleton-title" />
          <div className="draft-grid">
            <div className="draft-main">
              <div className="skeleton skeleton-card" />
              <div className="skeleton skeleton-card" />
            </div>
            <div className="skeleton skeleton-panel" />
          </div>
        </div>
      </div>
    );
  }
  if (failed || !draft) {
    return (
      <div className="draft-page">
        <FriendlyError
          debug={errorDebug}
          message={draftLoadErrorMessage(errorDebug, t)}
          onRetry={load}
        />
      </div>
    );
  }

  const manualPlatforms = selected.filter((slug) => slug !== "telegram");
  const disabledReason = computeReason();
  const primary = primaryAction();

  function computeReason(): string | null {
    if (draftEmpty) return "Черновик пуст — публикация недоступна.";
    if (mode === "manual") {
      if (!manualPlatforms.length) return "Выберите хотя бы один канал.";
      return null;
    }
    if (!selected.length) return "Выберите хотя бы один канал.";
    if (instagramNeedsMedia) {
      return "Добавьте изображение или видео для публикации в Instagram.";
    }
    if (mode === "schedule" && !scheduledTime) {
      return "Укажите дату и время публикации.";
    }
    return null;
  }

  function primaryAction() {
    if (mode === "manual") {
      return {
        label: "Подготовить пакет",
        busyLabel: "Готовим",
        onPrimary: makeManualPackage,
        disabled: publishing || draftEmpty || !manualPlatforms.length,
      };
    }
    return {
      label: mode === "schedule" ? "Запланировать" : "Опубликовать сейчас",
      busyLabel: "Отправляем",
      onPrimary: publish,
      disabled:
        publishing ||
        uploading ||
        generating ||
        draftEmpty ||
        !selected.length ||
        instagramNeedsMedia ||
        (mode === "schedule" && !scheduledTime),
    };
  }

  return (
    <div className="draft-page">
      <DraftHeader draft={draft} />

      <div className="draft-grid">
        <div className="draft-main">
          <DraftTextCard text={draft.text} channel={draft.channel} />
          <DraftPreviewCard
            media={attachedMedia}
            text={draft.text}
            username={instagramUsername}
          />
          <section className="draft-card draft-status-card">
            <div className="draft-card-head">
              <h2>{t("История и статус")}</h2>
            </div>
            <dl className="draft-meta">
              <div>
                <dt>{t("Статус")}</dt>
                <dd>
                  <Status value={draft.status}>{draft.status}</Status>
                </dd>
              </div>
              <div>
                <dt>{t("Обновлён")}</dt>
                <dd>{formatDate(draft.updated_at, locale)}</dd>
              </div>
              <div>
                <dt>{t("Версия")}</dt>
                <dd>{draft.version}</dd>
              </div>
              {draft.content_plan_id ? (
                <div>
                  <dt>{t("Источник")}</dt>
                  <dd>{t("Создан из контент-плана")}</dd>
                </div>
              ) : null}
              <div>
                <dt>Notion</dt>
                <dd>
                  <Status value={draft.notion_synced ? "active" : "disabled"}>
                    {draft.notion_synced
                      ? t("Сохранён в Notion")
                      : t("Не сохранён в Notion")}
                  </Status>
                </dd>
              </div>
            </dl>
          </section>
        </div>

        <aside className="publish-panel">
          <div className="publish-panel-scroll">
            <h2 className="publish-panel-title">{t("Публикация")}</h2>
            {!blotatoEnabled ? (
              <p className="plan-note plan-note-muted">
                {t("Blotato не подключён. Автопубликация в соцсети временно недоступна.")}
              </p>
            ) : null}

            <ChannelSelector
              channels={channels}
              selected={selected}
              onToggle={toggle}
            />

            <PublicationModeSelector mode={mode} onChange={setMode} />

            {mode === "schedule" ? (
              <label className="schedule-input">
                <span>{t("Дата и время публикации")}</span>
                <input
                  onChange={(event) => setScheduledTime(event.target.value)}
                  type="datetime-local"
                  value={scheduledTime}
                />
                <span className="draft-helper">
                  {t("Время указывается в вашем часовом поясе.")}
                </span>
              </label>
            ) : null}

            {mode !== "manual" ? (
              <section className="media-block">
                <div className="draft-card-head">
                  <h3 className="publish-subhead">{t("Медиа")}</h3>
                  <span className="muted">{attachedMedia.length}/10</span>
                </div>

                <MediaGrid
                  media={attachedMedia}
                  onRemove={removeMedia}
                  disabled={publishing}
                />

                <label
                  className={`button button-secondary button-small button-wide${uploading || generating ? " is-disabled" : ""}`}
                >
                  <Icon name={uploading ? "sync" : "upload"} />
                  {uploading ? t("Загружаем медиа") : t("Загрузить фото/видео")}
                  <input
                    accept={MEDIA_ACCEPT}
                    disabled={uploading || generating}
                    hidden
                    multiple
                    onChange={(event) => void uploadFiles(event.target.files)}
                    ref={mediaInputRef}
                    type="file"
                  />
                </label>

                <MediaGeneratorPanel
                  visualKind={visualKind}
                  onVisualKindChange={setVisualKind}
                  visualPrompt={visualPrompt}
                  onVisualPromptChange={setVisualPrompt}
                  generating={generating}
                  uploading={uploading}
                  generationStatus={generationStatus}
                  blotatoEnabled={blotatoEnabled}
                  onGenerate={() => void generateVisual()}
                  onCancel={cancelGeneration}
                />

                <label className="schedule-input">
                  <span>{t("Или вставьте публичную ссылку")}</span>
                  <input
                    onChange={(event) => setManualMediaUrl(event.target.value)}
                    placeholder="https://..."
                    type="url"
                    value={manualMediaUrl}
                  />
                </label>
              </section>
            ) : null}

            {actionError ? <FriendlyError message={actionError} /> : null}

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
          </div>

          <StickyPublishActions
            label={primary.label}
            busyLabel={primary.busyLabel}
            busy={publishing}
            disabled={primary.disabled}
            reason={disabledReason}
            onPrimary={primary.onPrimary}
          />
        </aside>
      </div>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

function submissionLabel(status: string): string {
  if (status === "published") return "Опубликовано";
  if (status === "submitted") return "Отправлено";
  if (status === "scheduled") return "Запланировано";
  if (status === "failed") return "Ошибка";
  if (status === "skipped") return "Пропущено";
  if (status === "unsupported") return "Не поддерживается";
  return status;
}

function draftLoadErrorMessage(
  debug: ApiDebugInfo | null,
  t: (value: string) => string,
): string {
  if (debug?.status === 404) {
    return t("Черновик не найден или у вашего аккаунта нет доступа к этому workspace.");
  }
  if (debug?.status === 403) {
    return t(debug.message || "У вашего аккаунта нет доступа к этому workspace.");
  }
  if (debug?.message) return t(debug.message);
  return t("Не удалось загрузить черновик. Попробуйте обновить страницу.");
}
