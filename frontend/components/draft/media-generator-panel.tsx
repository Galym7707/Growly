"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { useLanguage } from "@/lib/i18n";
import type { VideoProvider, VideoProvidersInfo } from "@/lib/media";

type VisualKind = "image" | "video";

export function MediaGeneratorPanel({
  visualKind,
  onVisualKindChange,
  visualPrompt,
  onVisualPromptChange,
  generating,
  uploading,
  generationStatus,
  blotatoEnabled,
  provider,
  onProviderChange,
  providers,
  onGenerate,
  onCancel,
}: {
  visualKind: VisualKind;
  onVisualKindChange: (kind: VisualKind) => void;
  visualPrompt: string;
  onVisualPromptChange: (prompt: string) => void;
  generating: boolean;
  uploading: boolean;
  generationStatus: string;
  blotatoEnabled: boolean;
  provider: VideoProvider;
  onProviderChange: (provider: VideoProvider) => void;
  providers: VideoProvidersInfo | null;
  onGenerate: () => void;
  onCancel: () => void;
}) {
  const { t } = useLanguage();
  // Open automatically while generating so the user keeps sight of progress.
  const [open, setOpen] = useState(false);
  const expanded = open || generating;

  const replicateEnabled = Boolean(providers?.replicate.enabled);
  const balance = providers?.credits.balance ?? 0;
  const videoCost = providers?.credits.video_cost ?? 1;

  // Replicate always produces video; the image kind stays on Blotato.
  const usingReplicate = provider === "replicate" && visualKind === "video";
  const notEnoughCredits = usingReplicate && balance < videoCost;
  const providerUnavailable = usingReplicate
    ? !replicateEnabled
    : !blotatoEnabled;

  return (
    <div className="ai-generator">
      <button
        aria-expanded={expanded}
        className="ai-generator-toggle"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <span>
          <Icon name="sparkles" />
          {t("AI-генерация медиа")}
        </span>
        <Icon name="chevron" className={expanded ? "is-open" : ""} />
      </button>

      {expanded ? (
        <div className="ai-generator-body">
          <label>
            <span>{t("Тип медиа")}</span>
            <select
              disabled={generating || uploading}
              onChange={(event) =>
                onVisualKindChange(event.target.value as VisualKind)
              }
              value={visualKind}
            >
              <option value="image">{t("Карусель изображений")}</option>
              <option value="video">{t("AI-видео")}</option>
            </select>
          </label>

          {visualKind === "video" && replicateEnabled ? (
            <label>
              <span>{t("Провайдер видео")}</span>
              <select
                disabled={generating || uploading}
                onChange={(event) =>
                  onProviderChange(event.target.value as VideoProvider)
                }
                value={provider}
              >
                <option value="blotato">{t("Blotato (шаблоны)")}</option>
                <option value="replicate">
                  {t("Replicate (за кредиты)")}
                </option>
              </select>
            </label>
          ) : null}

          {usingReplicate ? (
            <p className="media-generation-status">
              <Icon name="sparkles" />
              {t("Баланс кредитов")}: <strong>{balance}</strong>
              {" · "}
              {t("1 видео")} = {videoCost}{" "}
              {videoCost === 1 ? t("кредит") : t("кредита")}
            </p>
          ) : null}

          <label>
            <span>{t("Что должно быть на фото или видео")}</span>
            <textarea
              disabled={generating}
              onChange={(event) => onVisualPromptChange(event.target.value)}
              rows={4}
              value={visualPrompt}
            />
          </label>

          <div className="ai-generator-actions">
            <button
              className="button button-primary button-small"
              disabled={
                generating ||
                uploading ||
                !visualPrompt.trim() ||
                providerUnavailable ||
                notEnoughCredits
              }
              onClick={onGenerate}
              type="button"
            >
              <Icon name={generating ? "sync" : "sparkles"} />
              {generating ? t("Генерируем") : t("Сгенерировать")}
            </button>
            {generating ? (
              <button
                className="button button-secondary button-small"
                onClick={onCancel}
                type="button"
              >
                <Icon name="close" />
                {t("Отменить")}
              </button>
            ) : null}
          </div>

          {notEnoughCredits ? (
            <p className="media-generation-status">
              <Icon name="arrow" />
              {t("Недостаточно кредитов для генерации видео.")}{" "}
              <Link href="/settings/billing#credits">
                {t("Пополнить кредиты")}
              </Link>
            </p>
          ) : null}

          {generationStatus ? (
            <p className="media-generation-status">
              <Icon name={generating ? "sync" : "check"} />
              {generationStatus}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
