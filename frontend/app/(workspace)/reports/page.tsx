"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import {
  apiRequest,
  formatDate,
  formatReportTitle,
  formatReportType,
} from "@/lib/api";
import { useActiveContext } from "@/lib/active-context-provider";
import { shortConclusion } from "@/lib/report-sections";
import { useLanguage } from "@/lib/i18n";
import type { Report } from "@/lib/types";

export default function ReportsPage() {
  const [items, setItems] = useState<Report[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Report[] }>("/reports");
      setItems(response.items);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }, [t]);

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

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("База знаний")}
        title={t("Отчёты")}
        description={t("Рыночные, конкурентные и результативные отчёты с источниками и ограничениями.")}
        action={
          <Link className="button button-primary" href="/market-scan">
            <Icon name="plus" />
            {t("Новый анализ")}
          </Link>
        }
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {!loading && !error ? (
        <>
          <div className="list-toolbar">
            <input
              aria-label={t("Поиск по отчётам")}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("Найти отчёт")}
              value={query}
            />
            <span className="muted">{t("Всего: {count}", { count: visible.length })}</span>
          </div>
          {visible.length ? (
            <div className="report-card-list">
              {visible.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          ) : (
            <EmptyState
              action={t("Запустить анализ")}
              href="/market-scan"
              icon="report"
              text={t("Отчёты появятся после анализа рынка, конкурентов или публикаций.")}
              title={t("Пока нет отчётов")}
            />
          )}
        </>
      ) : null}
    </div>
  );
}

function ReportCard({ report }: { report: Report }) {
  const router = useRouter();
  const { locale, t } = useLanguage();
  const { setActiveReport } = useActiveContext();
  const [busy, setBusy] = useState<null | "plan" | "post" | "notion">(null);
  const [notice, setNotice] = useState("");

  async function useForContentPlan() {
    setBusy("plan");
    setNotice("");
    try {
      await setActiveReport(report.id);
      router.push("/content-plan");
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
      setBusy(null);
    }
  }

  async function useForPost() {
    setBusy("post");
    setNotice("");
    try {
      await setActiveReport(report.id);
      router.push("/create-post");
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
      setBusy(null);
    }
  }

  async function saveToNotion() {
    setBusy("notion");
    setNotice("");
    try {
      await apiRequest("/notion/sync", {
        method: "POST",
        body: JSON.stringify({ target: "report", target_id: report.id }),
      });
      setNotice(t("Сохранено в Notion"));
    } catch (value) {
      setNotice(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy(null);
    }
  }

  const summary = shortConclusion(report.summary, 3) || t("Краткий вывод не указан.");

  return (
    <article className="report-card-item">
      <div className="report-card-head">
        <div>
          <p className="eyebrow">{formatReportType(report.type, locale)}</p>
          <h3>{formatReportTitle(report.title, report.type, locale)}</h3>
        </div>
        <Status value={report.status}>{report.status}</Status>
      </div>
      <p className="report-card-summary">{summary}</p>
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
          className="button button-secondary button-small"
          disabled={busy !== null}
          onClick={useForContentPlan}
          type="button"
        >
          {busy === "plan" ? t("Открываем") : t("Создать контент-план")}
        </button>
        <button
          className="button button-secondary button-small"
          disabled={busy !== null}
          onClick={useForPost}
          type="button"
        >
          {busy === "post" ? t("Открываем") : t("Создать пост")}
        </button>
        <button
          className="button button-secondary button-small"
          disabled={busy !== null}
          onClick={saveToNotion}
          type="button"
        >
          {busy === "notion" ? t("Сохраняем") : t("Сохранить в Notion")}
        </button>
      </div>
      {notice ? <p className="report-card-notice">{notice}</p> : null}
    </article>
  );
}
