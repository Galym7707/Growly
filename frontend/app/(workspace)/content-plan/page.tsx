"use client";

import {
  FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ContentPlanForm } from "@/components/content-plan-form";
import { ContentPlanView } from "@/components/content-plan-view";
import { FriendlyError } from "@/components/friendly-error";
import { Icon } from "@/components/icons";
import { ReportPicker } from "@/components/report-picker";
import { SelectedReportCard } from "@/components/selected-report-card";
import { LoadingState, PageHeader } from "@/components/ui";
import {
  apiErrorDebugInfo,
  apiRequest,
  type ApiDebugInfo,
} from "@/lib/api";
import { contentPlanMode, contentPlanRequestBody } from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import { contentPlanPathFromGeneratedResponse } from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanResponse, Draft, Report } from "@/lib/types";

export default function ContentPlanPage() {
  return (
    <Suspense fallback={<div className="workspace-page" />}>
      <ContentPlanContent />
    </Suspense>
  );
}

function ContentPlanContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reportIdParam = searchParams.get("reportId");
  const { locale, t } = useLanguage();
  const { active, applyReport, loadActiveReport, clearActive } =
    useActiveContext();

  const [manual, setManual] = useState(false);
  const [pickingId, setPickingId] = useState<number | null>(null);
  const [hydrating, setHydrating] = useState(false);
  const [selectError, setSelectError] = useState(false);
  const [data, setData] = useState<ContentPlanResponse>({ items: [], source: null });
  const [loadingList, setLoadingList] = useState(true);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");

  const hydratedParam = useRef<string | null>(null);

  useEffect(() => {
    if (!reportIdParam || !/^\d+$/.test(reportIdParam)) return;
    if (hydratedParam.current === reportIdParam) return;
    if (active && active.report_id === Number(reportIdParam)) {
      hydratedParam.current = reportIdParam;
      return;
    }
    hydratedParam.current = reportIdParam;
    setSelectError(false);
    setHydrating(true);
    void loadActiveReport(Number(reportIdParam))
      .then((next) => {
        if (!next) setSelectError(true);
      })
      .finally(() => setHydrating(false));
  }, [reportIdParam, active, loadActiveReport]);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans");
      setData(response);
    } catch {
      setData({ items: [], source: null });
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  function handleSelect(report: Report) {
    setSelectError(false);
    setPickingId(report.id);
    // Apply synchronously from the report we already have — the UI flips into
    // selected-report mode immediately, without waiting on a network round-trip.
    const next = applyReport(report);
    setPickingId(null);
    if (!next) {
      setSelectError(true);
      return;
    }
    setManual(false);
    hydratedParam.current = String(report.id);
    router.replace(`/content-plan?reportId=${report.id}`);
  }

  function retrySelect() {
    setSelectError(false);
    hydratedParam.current = null;
    if (reportIdParam && /^\d+$/.test(reportIdParam)) {
      setHydrating(true);
      void loadActiveReport(Number(reportIdParam))
        .then((next) => {
          if (!next) setSelectError(true);
        })
        .finally(() => setHydrating(false));
    }
  }

  async function changeReport() {
    await clearActive();
    setManual(false);
    setSelectError(false);
    hydratedParam.current = null;
    router.replace("/content-plan");
  }

  const mode = contentPlanMode(active, manual);

  async function createDraft(itemId: number) {
    setDraftingId(itemId);
    setFeedback("");
    try {
      const response = await apiRequest<{ draft: Draft }>(
        `/content-plan/${itemId}/draft`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      setFeedback(
        t("Черновик «{name}» создан.", {
          name: response.draft.title || response.draft.id,
        }),
      );
      router.push("/drafts");
    } finally {
      setDraftingId(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Планирование")}
        title={t("Контент-план")}
        description={t(
          "Темы, форматы и задачи на неделю на основе сохранённых источников.",
        )}
      />

      {feedback ? <div className="feedback feedback-success">{feedback}</div> : null}

      {selectError ? (
        <div className="feedback feedback-error" role="alert">
          <p>{t("Не удалось выбрать отчёт. Попробуйте ещё раз.")}</p>
          <div className="feedback-actions">
            <button
              className="button button-secondary button-small"
              onClick={retrySelect}
              type="button"
            >
              {t("Повторить")}
            </button>
            {reportIdParam ? (
              <Link
                className="button button-secondary button-small"
                href={`/reports/${reportIdParam}`}
              >
                {t("Открыть отчёт")}
              </Link>
            ) : null}
            <button
              className="button button-secondary button-small"
              onClick={changeReport}
              type="button"
            >
              {t("Выбрать другой отчёт")}
            </button>
          </div>
        </div>
      ) : hydrating && !active ? (
        <LoadingState label={t("Загружаю контекст отчёта…")} />
      ) : mode === "form" && active ? (
        <>
          <SelectedReportCard
            active={active}
            heading={t("План будет создан на основе отчёта")}
          >
            <button
              className="button button-secondary button-small"
              onClick={changeReport}
              type="button"
            >
              {t("Изменить отчёт")}
            </button>
            <Link
              className="button button-secondary button-small"
              href={`/reports/${active.report_id}`}
            >
              {t("Открыть отчёт")}
            </Link>
          </SelectedReportCard>
          <ContentPlanForm active={active} key={active.report_id} />
        </>
      ) : mode === "manual" ? (
        <ManualPlanForm onBack={() => setManual(false)} />
      ) : (
        <ReportPicker
          title={t("Выберите отчёт, на основе которого создать контент-план")}
          manualLabel={t("Создать без отчёта")}
          onManual={() => setManual(true)}
          onSelect={handleSelect}
          selectingId={pickingId}
        />
      )}

      {loadingList ? (
        <LoadingState />
      ) : data.items.length ? (
        <ContentPlanView
          draftingId={draftingId}
          items={data.items}
          onCreateDraft={createDraft}
          source={data.source}
        />
      ) : null}
    </div>
  );
}

function ManualPlanForm({ onBack }: { onBack: () => void }) {
  const router = useRouter();
  const { locale, t } = useLanguage();
  const [objective, setObjective] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [debug, setDebug] = useState<ApiDebugInfo | null>(null);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setError("");
    setDebug(null);
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans", {
        method: "POST",
        body: JSON.stringify(contentPlanRequestBody(null, objective, locale)),
      });
      router.push(contentPlanPathFromGeneratedResponse(response) || "/content-plan");
    } catch (value) {
      setDebug(apiErrorDebugInfo(value));
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <form className="form-panel" onSubmit={generate}>
      <div className="section-heading">
        <h2>{t("Создать без отчёта")}</h2>
        <button
          className="button button-secondary button-small"
          onClick={onBack}
          type="button"
        >
          {t("Назад к выбору отчёта")}
        </button>
      </div>
      <label>
        <span>{t("Цель недели")}</span>
        <textarea
          onChange={(event) => setObjective(event.target.value)}
          placeholder={t(
            "Например: объяснить ценность услуги и получить заявки на консультацию",
          )}
          required
          value={objective}
        />
      </label>
      {error ? (
        <FriendlyError
          debug={debug}
          message={`${t("Не удалось создать контент-план.")} ${error}`}
        />
      ) : null}
      <div className="form-actions">
        <button className="button button-primary" disabled={generating}>
          <Icon name={generating ? "sync" : "book"} />
          {generating ? t("Формируем план") : t("Создать план")}
        </button>
      </div>
    </form>
  );
}
