"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import { FriendlyError } from "@/components/friendly-error";
import { LoadingState, Status } from "@/components/ui";
import {
  apiErrorDebugInfo,
  apiRequest,
  formatDate,
  formatReportTitle,
  formatReportType,
  type ApiDebugInfo,
} from "@/lib/api";
import { shortConclusion } from "@/lib/report-sections";
import { useLanguage } from "@/lib/i18n";
import type { Report } from "@/lib/types";

type Props = {
  title: string;
  description?: string;
  manualLabel?: string;
  onManual?: () => void;
  onSelect: (report: Report) => void | Promise<void>;
  selectingId?: number | null;
};

export function ReportPicker({
  title,
  description,
  manualLabel,
  onManual,
  onSelect,
  selectingId = null,
}: Props) {
  const { locale, t } = useLanguage();
  const [items, setItems] = useState<Report[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [errorDebug, setErrorDebug] = useState<ApiDebugInfo | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    setErrorDebug(null);
    try {
      const response = await apiRequest<{ items: Report[] }>("/reports");
      setItems(response.items);
    } catch (value) {
      setFailed(true);
      setErrorDebug(apiErrorDebugInfo(value));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => {
    const value = query.toLowerCase().trim();
    return value
      ? items.filter((item) =>
          `${item.title} ${item.summary} ${item.type}`
            .toLowerCase()
            .includes(value),
        )
      : items;
  }, [items, query]);

  if (loading) return <LoadingState label={t("Загрузка данных")} />;
  if (failed) return <FriendlyError debug={errorDebug} onRetry={load} />;

  if (!items.length) {
    return (
      <div className="empty-state">
        <span className="empty-icon">
          <Icon name="report" />
        </span>
        <h2>{t("Пока нет отчётов. Сначала запустите анализ рынка.")}</h2>
        <div className="empty-actions">
          <Link className="button button-primary" href="/market-scan">
            {t("Запустить анализ рынка")}
            <Icon name="arrow" />
          </Link>
          {onManual ? (
            <button
              className="button button-secondary"
              onClick={onManual}
              type="button"
            >
              {manualLabel || t("Создать вручную")}
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <section className="report-picker">
      <div className="report-picker-head">
        <div>
          <p className="eyebrow">{t("Выбор отчёта")}</p>
          <h2>{title}</h2>
          {description ? <p className="muted">{description}</p> : null}
        </div>
        {onManual ? (
          <button
            className="button button-secondary button-small"
            onClick={onManual}
            type="button"
          >
            {manualLabel || t("Создать вручную")}
          </button>
        ) : null}
      </div>
      <div className="list-toolbar">
        <input
          aria-label={t("Поиск по отчётам")}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("Найти отчёт")}
          value={query}
        />
        <span className="muted">{t("Всего: {count}", { count: visible.length })}</span>
      </div>
      <div className="report-card-list">
        {visible.map((report, index) => (
          <article
            className={`report-card-item${index === 0 && !query ? " report-card-latest" : ""}`}
            key={report.id}
          >
            <div className="report-card-head">
              <div>
                <p className="eyebrow">
                  {formatReportType(report.type, locale)}
                  {index === 0 && !query ? ` · ${t("Последний")}` : ""}
                </p>
                <h3>{formatReportTitle(report.title, report.type, locale)}</h3>
              </div>
              <Status value={report.status}>{report.status}</Status>
            </div>
            <p className="report-card-summary">
              {shortConclusion(report.summary, 2) || t("Краткий вывод не указан.")}
            </p>
            <div className="report-card-meta">
              <span>{formatDate(report.created_at, locale)}</span>
              <span>{t("{count} источников", { count: report.sources_count })}</span>
            </div>
            <div className="report-card-actions">
              <Link
                className="button button-secondary button-small"
                href={`/reports/${report.id}`}
              >
                {t("Открыть")}
              </Link>
              <button
                className="button button-primary button-small"
                disabled={selectingId !== null}
                onClick={() => void onSelect(report)}
                type="button"
              >
                {selectingId === report.id
                  ? t("Открываем")
                  : t("Использовать этот отчёт")}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
