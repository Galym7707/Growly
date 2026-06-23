"use client";

import { useState } from "react";
import { Icon } from "@/components/icons";
import { useLanguage } from "@/lib/i18n";
import type { AttachedMedia } from "@/lib/media";

const COLLAPSED_COUNT = 4;

export function MediaGrid({
  media,
  onRemove,
  disabled,
}: {
  media: AttachedMedia[];
  onRemove: (url: string) => void;
  disabled?: boolean;
}) {
  const { t } = useLanguage();
  const [showAll, setShowAll] = useState(false);
  if (!media.length) return null;

  const visible = showAll ? media : media.slice(0, COLLAPSED_COUNT);

  return (
    <div className="media-grid-wrap">
      <div className="media-grid">
        {visible.map((item, index) => (
          <figure className="media-tile" key={item.url}>
            {item.kind === "video" ? (
              <video controls={false} muted preload="metadata" src={item.url} />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt="" src={item.url} />
            )}
            <figcaption>{`AI ${index + 1}`}</figcaption>
            <button
              aria-label={t("Удалить медиа")}
              className="media-tile-remove"
              disabled={disabled}
              onClick={() => onRemove(item.url)}
              title={t("Удалить медиа")}
              type="button"
            >
              <Icon name="close" />
            </button>
          </figure>
        ))}
      </div>
      {media.length > COLLAPSED_COUNT ? (
        <button
          className="text-link media-grid-toggle"
          onClick={() => setShowAll((value) => !value)}
          type="button"
        >
          {showAll
            ? t("Свернуть")
            : t("Показать все {count}", { count: media.length })}
        </button>
      ) : null}
    </div>
  );
}
