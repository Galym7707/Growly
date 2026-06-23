"use client";

import { useLanguage } from "@/lib/i18n";

export function DraftTextCard({
  text,
  channel,
}: {
  text: string;
  channel: string | null;
}) {
  const { t } = useLanguage();
  const trimmed = text.trim();
  const words = trimmed ? trimmed.split(/\s+/).length : 0;
  const isInstagram = (channel || "").toLowerCase().includes("instagram");

  return (
    <section className="draft-card">
      <div className="draft-card-head">
        <h2>{t("Текст публикации")}</h2>
        <span className="draft-counter">
          {t("{count} слов", { count: words })} · {text.length}
        </span>
      </div>
      {trimmed ? (
        <div className="draft-post-text">{text}</div>
      ) : (
        <p className="draft-placeholder-text">
          {t("Черновик пуст — публикация недоступна.")}
        </p>
      )}
      {isInstagram ? (
        <p className="draft-helper">
          {t("Оптимально до 125–150 слов для поста.")}
        </p>
      ) : null}
    </section>
  );
}
