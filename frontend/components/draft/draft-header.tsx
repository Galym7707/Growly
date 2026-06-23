"use client";

import Link from "next/link";
import { Status } from "@/components/ui";
import { formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Draft } from "@/lib/types";

export function DraftHeader({ draft }: { draft: Draft }) {
  const { locale, t } = useLanguage();
  const channel = draft.channel || t("Канал не указан");
  const title = draft.title || `${t("Черновик")} ${draft.id}`;

  return (
    <header className="draft-header">
      <div className="draft-breadcrumb">
        <Link href="/drafts">{t("Черновики")}</Link>
        <span aria-hidden="true">/</span>
        <span>{channel}</span>
        <span aria-hidden="true">/</span>
        <span>{t("версия {version}", { version: draft.version })}</span>
        <Link className="draft-breadcrumb-back text-link" href="/drafts">
          {t("Все черновики")}
        </Link>
      </div>

      <h1 className="draft-title">{title}</h1>

      <div className="draft-badges">
        <Status value={draft.status}>{draft.status}</Status>
        <span className="draft-badge">{formatDate(draft.updated_at, locale)}</span>
        {draft.channel ? (
          <span className="draft-badge draft-badge-channel">{draft.channel}</span>
        ) : null}
        <span className="draft-badge">
          {t("версия {version}", { version: draft.version })}
        </span>
      </div>
    </header>
  );
}
