"use client";

import { useLanguage } from "@/lib/i18n";

export type PublishMode = "now" | "schedule" | "manual";

const MODES: { value: PublishMode; title: string; hint: string }[] = [
  { value: "now", title: "Опубликовать сейчас", hint: "Пост уйдёт в выбранные соцсети сразу." },
  { value: "schedule", title: "Запланировать", hint: "Выберите дату и время публикации." },
  { value: "manual", title: "Пакет для ручной публикации", hint: "Готовый текст и медиа для ручного постинга." },
];

export function PublicationModeSelector({
  mode,
  onChange,
}: {
  mode: PublishMode;
  onChange: (mode: PublishMode) => void;
}) {
  const { t } = useLanguage();
  return (
    <div className="mode-selector">
      <h3 className="publish-subhead">{t("Когда публиковать")}</h3>
      <div className="mode-cards">
        {MODES.map((item) => (
          <label
            className={`mode-card${mode === item.value ? " is-selected" : ""}`}
            key={item.value}
          >
            <input
              checked={mode === item.value}
              name="publish-mode"
              onChange={() => onChange(item.value)}
              type="radio"
            />
            <span className="mode-card-body">
              <span className="mode-card-title">{t(item.title)}</span>
              <span className="mode-card-hint">{t(item.hint)}</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
