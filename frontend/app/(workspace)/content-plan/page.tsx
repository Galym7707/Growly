"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ContentPlanErrorPanel } from "@/components/content-plan-error";
import { ContentPlanView } from "@/components/content-plan-view";
import { Icon } from "@/components/icons";
import { LoadingState, PageHeader } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import {
  activeContextTopic,
  contentPlanRequestBody,
} from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { contentPlanPathFromGeneratedResponse } from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanResponse, Draft } from "@/lib/types";

export default function ContentPlanPage() {
  const [data, setData] = useState<ContentPlanResponse>({
    items: [],
    source: null,
  });
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loadErrorDebug, setLoadErrorDebug] = useState<ApiDebugInfo | null>(
    null,
  );
  const [actionErrorDebug, setActionErrorDebug] = useState<ApiDebugInfo | null>(
    null,
  );
  const [feedback, setFeedback] = useState("");
  const router = useRouter();
  const { locale, t } = useLanguage();
  const { active } = useActiveContext();
  const copy = contentPlanCopy(locale);
  const activeTopic = activeContextTopic(active);

  function friendlyActionReason(value: unknown): string {
    const debugInfo = apiErrorDebugInfo(value);
    const isNotFound =
      debugInfo?.status === 404 ||
      debugInfo?.message.trim().toLowerCase() === "not found";
    if (isNotFound) return copy.loadErrorReasons[2];
    return value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setLoadErrorDebug(null);
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans");
      setData(response);
    } catch (value) {
      setLoadErrorDebug(
        apiErrorDebugInfo(value) || { message: "", status: 0, url: "" },
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setError("");
    setActionErrorDebug(null);
    setFeedback("");
    try {
      const effectiveObjective =
        objective.trim() ||
        (activeTopic
          ? t("Контент-план по нише: {topic}", { topic: activeTopic })
          : objective);
      const response = await apiRequest<ContentPlanResponse>("/content-plans", {
        method: "POST",
        body: JSON.stringify(
          contentPlanRequestBody(active, effectiveObjective, locale),
        ),
      });
      setData(response);
      setLoadErrorDebug(null);
      setFeedback(t("Создано элементов: {count}.", { count: response.items.length }));
      setObjective("");
      router.push(contentPlanPathFromGeneratedResponse(response) || "/content-plan");
    } catch (value) {
      const reason = friendlyActionReason(value);
      setActionErrorDebug(apiErrorDebugInfo(value));
      setError(
        `${t("Не удалось создать контент-план.")} ${t("Причина: {reason}", {
          reason,
        })}`,
      );
    } finally {
      setGenerating(false);
    }
  }

  async function createDraft(itemId: number) {
    setDraftingId(itemId);
    setError("");
    setActionErrorDebug(null);
    setFeedback("");
    try {
      const response = await apiRequest<{ draft: Draft }>(
        `/content-plan/${itemId}/draft`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      setFeedback(t("Черновик «{name}» создан.", {
        name: response.draft.title || response.draft.id,
      }));
      router.push("/drafts");
    } catch (value) {
      setActionErrorDebug(apiErrorDebugInfo(value));
      setError(friendlyActionReason(value));
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
      <form className="form-panel" id="new-plan" onSubmit={generate}>
        <h2>{copy.newPlan}</h2>
        <p>
          {t(
            "Укажите бизнес-цель на неделю. Growly использует последние отчёты и материалы источников.",
          )}
        </p>
        {active && activeTopic ? (
          <div className="active-source">
            <div>
              <p className="eyebrow">{copy.basedOn}</p>
              <p className="active-source-topic">
                {t("План будет создан на основе анализа: {topic}", {
                  topic: activeTopic,
                })}
              </p>
              <p className="active-source-meta">
                {t("{count} источников", { count: active.sources_count })}
              </p>
            </div>
            <Link className="button button-secondary button-small" href="/reports">
              {t("Изменить источник")}
            </Link>
          </div>
        ) : null}
        <label>
          <span>{t("Цель недели")}</span>
          <textarea
            onChange={(event) => setObjective(event.target.value)}
            placeholder={copy.goalPlaceholder}
            required={!active}
            value={objective}
          />
        </label>
        <div className="form-actions">
          <button className="button button-primary" disabled={generating}>
            <Icon name={generating ? "sync" : "book"} />
            {generating ? t("Формируем план") : t("Создать план")}
          </button>
        </div>
      </form>

      {error ? (
        <div className="feedback feedback-error">
          {error}
          {process.env.NODE_ENV === "development" && actionErrorDebug ? (
            <div className="api-debug api-debug-inline">
              <div>
                <strong>Requested URL</strong>
                <span>{actionErrorDebug.url}</span>
              </div>
              <div>
                <strong>Status code</strong>
                <span>{actionErrorDebug.status}</span>
              </div>
              <div>
                <strong>Response message</strong>
                <span>{actionErrorDebug.message}</span>
              </div>
            </div>
          ) : null}
          <div className="feedback-actions">
            <button
              className="button button-secondary button-small"
              onClick={() => {
                setError("");
                setActionErrorDebug(null);
                void load();
              }}
              type="button"
            >
              {copy.retry}
            </button>
            <Link className="button button-secondary button-small" href="/reports">
              {copy.openReports}
            </Link>
            <a className="button button-secondary button-small" href="#new-plan">
              {copy.manualCreate}
            </a>
          </div>
        </div>
      ) : null}
      {feedback ? (
        <div className="feedback feedback-success">{feedback}</div>
      ) : null}

      {loading ? <LoadingState /> : null}
      {!loading && loadErrorDebug ? (
        <ContentPlanErrorPanel
          debugInfo={loadErrorDebug}
          onRetry={() => {
            setLoadErrorDebug(null);
            void load();
          }}
        />
      ) : null}
      {!loading && !loadErrorDebug ? (
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
