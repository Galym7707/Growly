"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { ReportView } from "@/components/report-view";
import {
  CopyShareLinkButton,
  ShareWithTeamButton,
} from "@/components/team/share-controls";
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
  formatStatusLabel,
} from "@/lib/api";
import { useActiveContext } from "@/lib/active-context-provider";
import type { Report } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [routing, setRouting] = useState<null | "plan" | "post">(null);
  const { locale, t } = useLanguage();
  const { applyReport } = useActiveContext();

  function continueWith(target: "plan" | "post") {
    setRouting(target);
    if (report) applyReport(report);
    const id = report?.id ?? params.id;
    router.push(
      target === "plan"
        ? `/content-plan?reportId=${id}`
        : `/create-post?reportId=${id}`,
    );
  }

  const load = useCallback(async () => {
    setError("");
    try {
      const response = await apiRequest<{ report: Report }>(
        `/reports/${params.id}`,
      );
      setReport(response.report);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    }
  }, [params.id, t]);

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
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="workspace-page">
      {!report && !error ? <LoadingState label={t("Загружаем отчёт")} /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {report ? (
        <>
          <PageHeader
            eyebrow={formatReportType(report.type, locale)}
            title={formatReportTitle(report.title, report.type, locale)}
            description={report.query || t("Сформировано Growly")}
            action={
              <div className="header-actions">
                <ShareWithTeamButton />
                {Number.isFinite(Number(params.id)) ? (
                  <CopyShareLinkButton
                    resourceType="report"
                    resourceId={Number(params.id)}
                  />
                ) : null}
                <button
                  className="button button-secondary"
                  disabled={syncing}
                  onClick={syncNotion}
                  type="button"
                >
                  <Icon name="notion" />
                  {t(syncing ? "Сохраняем" : "Сохранить в Notion")}
                </button>
              </div>
            }
          />
          <div className="report-layout">
            <main className="report-main">
              <ReportView report={report} />
            </main>
            <aside className="report-aside">
              <dl>
                <div>
                  <dt>{t("Статус")}</dt>
                  <dd>
                    <Status value={report.status}>
                      {formatStatusLabel(report.status, locale)}
                    </Status>
                  </dd>
                </div>
                <div>
                  <dt>{t("Дата")}</dt>
                  <dd>{formatDate(report.created_at, locale)}</dd>
                </div>
                <div>
                  <dt>{t("Источники")}</dt>
                  <dd>{report.sources_count}</dd>
                </div>
                <div>
                  <dt>Notion</dt>
                  <dd>{t(report.notion_synced ? "Синхронизирован" : "Не сохранён")}</dd>
                </div>
              </dl>
              {report.notion_url ? (
                <a
                  className="button button-secondary button-wide"
                  href={report.notion_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {t("Открыть Notion")}
                  <Icon name="external" />
                </a>
              ) : null}
              <div className="report-aside-actions">
                <button
                  className="button button-secondary button-wide"
                  disabled={routing !== null}
                  onClick={() => continueWith("plan")}
                  type="button"
                >
                  <Icon name="book" />
                  {t("Создать контент-план")}
                </button>
                <button
                  className="button button-secondary button-wide"
                  disabled={routing !== null}
                  onClick={() => continueWith("post")}
                  type="button"
                >
                  <Icon name="draft" />
                  {t("Создать пост")}
                </button>
              </div>
              <Link className="text-link" href="/reports">
                {t("Вернуться к отчётам")}
              </Link>
            </aside>
          </div>
        </>
      ) : null}
    </div>
  );
}
