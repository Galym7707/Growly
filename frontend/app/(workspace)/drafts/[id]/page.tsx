"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
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
import {
  MEDIA_ACCEPT,
  isAllowedMediaFile,
  mediaKind,
  mergeMedia,
  visualStatusLabel,
  type AttachedMedia,
} from "@/lib/media";
import type { Draft } from "@/lib/types";

type Mode = "now" | "schedule" | "manual";
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

  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);

  const [selected, setSelected] = useState<string[]>([]);
  const [mode, setMode] = useState<Mode>(
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

  const draftEmpty = !draft || !draft.text || !draft.text.trim();
  const mediaUrls = Array.from(
    new Set([
      ...attachedMedia.map((item) => item.url),
      ...(manualMediaUrl.trim() ? [manualMediaUrl.trim()] : []),
    ]),
  );
  // Instagram requires at least one image or video to publish.
  const instagramNeedsMedia =
    selected.includes("instagram") && mediaUrls.length === 0;

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
        },
      );
      if (!visual.id) {
        throw new Error(t("Blotato не вернул ID созданного медиа."));
      }
      const visualId = visual.id;
      for (let attempt = 0; attempt < VISUAL_POLL_ATTEMPTS; attempt += 1) {
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
          return;
        }
        if (visual.status === "creation-from-template-failed") {
          throw new Error(t("Blotato не удалось сгенерировать медиа."));
        }
        await new Promise((resolve) =>
          window.setTimeout(resolve, VISUAL_POLL_INTERVAL_MS),
        );
        visual = await apiRequest<VisualResult>(
          `/integrations/blotato/visuals/${encodeURIComponent(visualId)}`,
        );
      }
      throw new Error(
        t("Генерация заняла слишком много времени. Проверьте результат в Blotato."),
      );
    } catch (value) {
      setGenerationStatus("");
      setActionError(
        value instanceof Error
          ? t(value.message)
          : t("Blotato не удалось сгенерировать медиа."),
      );
    } finally {
      setGenerating(false);
    }
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

          {mode !== "manual" ? (
            <section className="media-tools" aria-labelledby="media-tools-title">
              <div className="media-tools-heading">
                <div>
                  <h3 id="media-tools-title">{t("Медиа")}</h3>
                  <span className="muted">
                    {t("Фото, видео или карусель для публикации")}
                  </span>
                </div>
                <label
                  className={`button button-secondary button-small${uploading || generating ? " is-disabled" : ""}`}
                >
                  <Icon name={uploading ? "sync" : "plus"} />
                  {uploading
                    ? t("Загружаем медиа")
                    : t("Загрузить фото или видео")}
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
              </div>

              {attachedMedia.length ? (
                <div className="media-preview-list">
                  {attachedMedia.map((item) => (
                    <article className="media-preview" key={item.url}>
                      <div className="media-preview-asset">
                        {item.kind === "video" ? (
                          <video controls={false} muted preload="metadata" src={item.url} />
                        ) : (
                          // Remote Blotato hosts are dynamic, so Next Image cannot be preconfigured safely.
                          // eslint-disable-next-line @next/next/no-img-element
                          <img alt="" src={item.url} />
                        )}
                      </div>
                      <span title={item.name}>{item.name}</span>
                      <button
                        aria-label={t("Удалить медиа")}
                        className="icon-button"
                        disabled={publishing}
                        onClick={() =>
                          setAttachedMedia((current) =>
                            current.filter((media) => media.url !== item.url),
                          )
                        }
                        title={t("Удалить медиа")}
                        type="button"
                      >
                        <Icon name="close" />
                      </button>
                    </article>
                  ))}
                </div>
              ) : null}

              <div className="media-generator">
                <div className="media-generator-controls">
                  <label>
                    <span>{t("Генерация в Blotato")}</span>
                    <select
                      disabled={generating || uploading}
                      onChange={(event) =>
                        setVisualKind(event.target.value as VisualKind)
                      }
                      value={visualKind}
                    >
                      <option value="image">{t("Карусель изображений")}</option>
                      <option value="video">{t("AI-видео")}</option>
                    </select>
                  </label>
                  <button
                    className="button button-secondary"
                    disabled={
                      generating || uploading || !visualPrompt.trim() || !blotatoEnabled
                    }
                    onClick={() => void generateVisual()}
                    type="button"
                  >
                    <Icon name={generating ? "sync" : "plus"} />
                    {generating ? t("Генерируем") : t("Сгенерировать")}
                  </button>
                </div>
                <label>
                  <span>{t("Что должно быть на фото или видео")}</span>
                  <textarea
                    disabled={generating}
                    onChange={(event) => setVisualPrompt(event.target.value)}
                    rows={4}
                    value={visualPrompt}
                  />
                </label>
                {generationStatus ? (
                  <p className="media-generation-status">
                    <Icon name={generating ? "sync" : "check"} />
                    {generationStatus}
                  </p>
                ) : null}
              </div>

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
                  uploading ||
                  generating ||
                  draftEmpty ||
                  !selected.length ||
                  instagramNeedsMedia ||
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
          {instagramNeedsMedia && mode !== "manual" ? (
            <p className="plan-note plan-note-muted">
              {t("Для публикации в Instagram добавьте изображение или видео.")}
            </p>
          ) : null}

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
