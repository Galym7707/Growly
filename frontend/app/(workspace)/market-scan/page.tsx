"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { reportPathFromGeneratedResponse } from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";
import {
  isFailedMarketScanJob,
  marketScanErrorMessage,
  marketScanJobPath,
  marketScanStepIndex,
  type MarketScanJobResponse,
} from "@/lib/market-scan-job";
import type { Report } from "@/lib/types";

const steps = [
  "Ищу источники",
  "Сохраняю данные",
  "Анализирую",
  "Формирую отчёт",
  "Синхронизирую с Notion",
];

type MarketScanResponse = MarketScanJobResponse & {
  id?: number | string;
  reportId?: number | string;
  report?: Report;
};

const MARKET_SCAN_POLL_INTERVAL_MS = 3_000;
const MARKET_SCAN_POLL_ATTEMPTS = 300;

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForMarketScan(
  jobId: number | string,
  onProgress: (response: MarketScanResponse) => void,
): Promise<MarketScanResponse> {
  for (let attempt = 0; attempt < MARKET_SCAN_POLL_ATTEMPTS; attempt += 1) {
    if (attempt > 0) await delay(MARKET_SCAN_POLL_INTERVAL_MS);
    const response = await apiRequest<MarketScanResponse>(
      marketScanJobPath(jobId),
    );
    onProgress(response);
    if (reportPathFromGeneratedResponse(response)) return response;
    if (isFailedMarketScanJob(response.status)) {
      throw new Error(
        response.error_message || "Не удалось завершить анализ рынка.",
      );
    }
    if (["completed", "analysis_pending"].includes(response.status || "")) {
      return response;
    }
  }
  throw new Error("Анализ занимает больше времени, чем ожидалось.");
}

export default function MarketScanPage() {
  const [niche, setNiche] = useState("");
  const [region, setRegion] = useState("Казахстан, русский язык");
  const [competitors, setCompetitors] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<{
    reportPath: string | null;
    sourcesCount: number;
  } | null>(null);
  const router = useRouter();
  const { locale, t } = useLanguage();

  useEffect(() => {
    setRegion(
      locale === "en"
        ? "Kazakhstan, English"
        : locale === "kk"
          ? "Қазақстан, қазақ тілі"
          : "Казахстан, русский язык",
    );
  }, [locale]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(null);
    setActiveStep(0);
    try {
      let response = await apiRequest<MarketScanResponse>("/market-scan", {
        method: "POST",
        body: JSON.stringify({
          niche,
          region_language: region,
          competitor_keywords: competitors,
          language: locale,
        }),
      });
      if (!reportPathFromGeneratedResponse(response) && response.job_id) {
        response = await waitForMarketScan(response.job_id, (job) => {
          setActiveStep(marketScanStepIndex(job.current_step));
        });
      }
      const reportPath = reportPathFromGeneratedResponse(response);
      setSuccess({
        reportPath,
        sourcesCount:
          response.sources_saved ??
          response.sources_count ??
          response.report?.sources_count ??
          0,
      });
      if (reportPath) {
        router.push(reportPath);
      }
    } catch (value) {
      const message =
        value instanceof Error ? value.message : "Неизвестная ошибка";
      setError(
        t(marketScanErrorMessage(message)),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Исследование")}
        title={t("Анализ рынка")}
        description={t("Growly сначала сохраняет публичные источники, затем формирует выводы и отчёт.")}
      />
      <form className="form-panel" onSubmit={submit}>
        <h2>{t("Параметры анализа")}</h2>
        <p>
          {t("Опишите рынок достаточно конкретно, чтобы поиск не смешивал разные категории.")}
        </p>
        <div className="form-grid">
          <label className="full">
            <span>{t("Ниша или продукт")}</span>
            <input
              onChange={(event) => setNiche(event.target.value)}
              placeholder={t("Например: доставка здорового питания для офисов")}
              required
              value={niche}
            />
          </label>
          <label>
            <span>{t("Регион и язык")}</span>
            <input
              onChange={(event) => setRegion(event.target.value)}
              required
              value={region}
            />
          </label>
          <label>
            <span>{t("Известные конкуренты")}</span>
            <input
              onChange={(event) => setCompetitors(event.target.value)}
              placeholder={t("Можно оставить пустым")}
              value={competitors}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="button button-primary" disabled={loading}>
            <Icon name={loading ? "sync" : "search"} />
            {t(loading ? "Анализ выполняется" : "Запустить анализ")}
          </button>
        </div>
      </form>
      {loading ? (
        <div className="task-progress" aria-live="polite">
          {steps.map((step, index) => (
            <div
              className={
                index < activeStep
                  ? "done"
                  : index === activeStep
                    ? "active"
                    : ""
              }
              key={step}
            >
              <Icon
                name={
                  index < activeStep
                    ? "check"
                    : index === activeStep
                      ? "sync"
                      : "chevron"
                }
              />
              {t(step)}
            </div>
          ))}
        </div>
      ) : null}
      {error ? <div className="feedback feedback-error">{error}</div> : null}
      {success ? (
        <div className="feedback feedback-success">
          {success.reportPath
            ? t("Отчёт готов. Сохранено источников: {count}.", {
                count: success.sourcesCount,
              })
            : t("Отчёт создан, но ссылка на него не получена. Откройте раздел Отчёты.")}
          <div className="feedback-actions">
            {success.reportPath ? (
              <Link className="button button-secondary button-small" href={success.reportPath}>
                {t("Открыть отчёт")}
                <Icon name="arrow" />
              </Link>
            ) : (
              <Link className="button button-secondary button-small" href="/reports">
                {t("Открыть отчёты")}
                <Icon name="arrow" />
              </Link>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
