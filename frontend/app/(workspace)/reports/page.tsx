"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import { apiRequest, formatDate, formatReportTitle } from "@/lib/api";
import type { Report } from "@/lib/types";

export default function ReportsPage() {
  const [items, setItems] = useState<Report[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Report[] }>("/reports");
      setItems(response.items);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
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

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="База знаний"
        title="Отчёты"
        description="Рыночные, конкурентные и результативные отчёты с источниками и ограничениями."
        action={
          <Link className="button button-primary" href="/market-scan">
            <Icon name="plus" />
            Новый анализ
          </Link>
        }
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {!loading && !error ? (
        <>
          <div className="list-toolbar">
            <input
              aria-label="Поиск по отчётам"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Найти отчёт"
              value={query}
            />
            <span className="muted">Всего: {visible.length}</span>
          </div>
          {visible.length ? (
            <div className="report-list">
              {visible.map((report) => (
                <Link href={`/reports/${report.id}`} key={report.id}>
                  <div>
                    <h3>{formatReportTitle(report.title, report.type)}</h3>
                    <p>{report.summary || "Краткий вывод не указан."}</p>
                  </div>
                  <span className="meta">{report.sources_count} источников</span>
                  <div>
                    <Status value={report.status}>{report.status}</Status>
                    <span className="meta">{formatDate(report.created_at)}</span>
                  </div>
                  <Icon name="arrow" />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              action="Запустить анализ"
              href="/market-scan"
              icon="report"
              text="Отчёты появятся после анализа рынка, конкурентов или публикаций."
              title="Пока нет отчётов"
            />
          )}
        </>
      ) : null}
    </div>
  );
}
