"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { ReportView } from "@/components/report-view";
import {
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
import type { Report } from "@/lib/types";

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const response = await apiRequest<{ report: Report }>(
        `/reports/${params.id}`,
      );
      setReport(response.report);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function syncNotion() {
    setSyncing(true);
    setError("");
    try {
      await apiRequest("/notion/sync", {
        method: "POST",
        body: JSON.stringify({
          target: "report",
          target_id: Number(params.id),
        }),
      });
      await load();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="workspace-page">
      {!report && !error ? <LoadingState label="Загружаем отчёт" /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {report ? (
        <>
          <PageHeader
            eyebrow={formatReportType(report.type)}
            title={formatReportTitle(report.title, report.type)}
            description={report.query || "Сформировано Growly"}
            action={
              <button
                className="button button-secondary"
                disabled={syncing}
                onClick={syncNotion}
                type="button"
              >
                <Icon name="notion" />
                {syncing ? "Сохраняем" : "Сохранить в Notion"}
              </button>
            }
          />
          <div className="report-layout">
            <main className="report-main">
              <ReportView report={report} />
            </main>
            <aside className="report-aside">
              <dl>
                <div>
                  <dt>Статус</dt>
                  <dd>
                    <Status value={report.status}>{report.status}</Status>
                  </dd>
                </div>
                <div>
                  <dt>Дата</dt>
                  <dd>{formatDate(report.created_at)}</dd>
                </div>
                <div>
                  <dt>Источники</dt>
                  <dd>{report.sources_count}</dd>
                </div>
                <div>
                  <dt>Notion</dt>
                  <dd>{report.notion_synced ? "Синхронизирован" : "Не сохранён"}</dd>
                </div>
              </dl>
              {report.notion_url ? (
                <a
                  className="button button-secondary button-wide"
                  href={report.notion_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Открыть Notion
                  <Icon name="external" />
                </a>
              ) : null}
              <Link className="text-link" href="/reports">
                Вернуться к отчётам
              </Link>
            </aside>
          </div>
        </>
      ) : null}
    </div>
  );
}
