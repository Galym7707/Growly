"use client";

import type { ReactNode } from "react";
import { formatDate } from "@/lib/api";
import { activeContextTopic, type ActiveContext } from "@/lib/active-context";
import { useLanguage } from "@/lib/i18n";

export function SelectedReportCard({
  active,
  heading,
  children,
}: {
  active: ActiveContext;
  heading: string;
  children?: ReactNode;
}) {
  const { locale, t } = useLanguage();
  const topic = activeContextTopic(active);

  return (
    <div className="context-card">
      <div className="context-card-head">
        <p className="eyebrow">{heading}</p>
        <h2>{active.report_title || topic || t("Отчёт")}</h2>
        <p className="context-card-meta">
          {t("Источников: {count}", { count: active.sources_count })}
          {active.created_at
            ? ` · ${t("Дата")}: ${formatDate(active.created_at, locale)}`
            : ""}
        </p>
      </div>
      {children ? <div className="context-card-actions">{children}</div> : null}
    </div>
  );
}
