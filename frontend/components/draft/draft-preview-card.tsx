"use client";

import { Icon } from "@/components/icons";
import { useLanguage } from "@/lib/i18n";
import type { AttachedMedia } from "@/lib/media";

export function DraftPreviewCard({
  media,
  text,
  username,
}: {
  media: AttachedMedia[];
  text: string;
  username: string | null;
}) {
  const { t } = useLanguage();
  const cover = media[0];
  const handle = username ? `@${username.replace(/^@/, "")}` : t("Нет аккаунта");

  return (
    <section className="draft-card">
      <div className="draft-card-head">
        <h2>{t("Preview")}</h2>
        {media.length > 1 ? (
          <span className="draft-counter">
            <Icon name="layers" /> {media.length}
          </span>
        ) : null}
      </div>

      <div className="ig-preview">
        <div className="ig-preview-top">
          <span className="ig-avatar" aria-hidden="true">
            {handle.slice(1, 2).toUpperCase()}
          </span>
          <span className="ig-handle">{handle}</span>
        </div>

        <div className="ig-preview-media">
          {cover ? (
            cover.kind === "video" ? (
              <video controls={false} muted preload="metadata" src={cover.url} />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt="" src={cover.url} />
            )
          ) : (
            <div className="ig-preview-empty">
              <Icon name="image" />
              <p>{t("Добавьте изображение или видео для Instagram")}</p>
            </div>
          )}
          {media.length > 1 ? (
            <div className="ig-preview-dots" aria-hidden="true">
              {media.slice(0, 6).map((item, index) => (
                <span
                  className={index === 0 ? "is-active" : ""}
                  key={item.url}
                />
              ))}
            </div>
          ) : null}
        </div>

        {text.trim() ? (
          <p className="ig-preview-caption">
            <strong>{handle}</strong> {text}
          </p>
        ) : null}
      </div>
    </section>
  );
}
