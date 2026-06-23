"use client";

import { useState } from "react";
import { Icon } from "@/components/icons";
import { useLanguage } from "@/lib/i18n";

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
  onGenerate: () => void;
  onCancel: () => void;
}) {
  const { t } = useLanguage();
  // Open automatically while generating so the user keeps sight of progress.
  const [open, setOpen] = useState(false);
  const expanded = open || generating;

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
                generating || uploading || !visualPrompt.trim() || !blotatoEnabled
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
