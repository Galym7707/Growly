"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ContentPlanView } from "@/components/content-plan-view";
import { Icon } from "@/components/icons";
import { LoadingState, PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
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
  const [feedback, setFeedback] = useState("");
  const router = useRouter();
  const { locale, t } = useLanguage();
  const copy = contentPlanCopy(locale);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans");
      setData(response);
    } catch (value) {
      setError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setError("");
    setFeedback("");
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans", {
        method: "POST",
        body: JSON.stringify({
          weekly_objective: objective,
          business: { language: locale },
          language: locale,
        }),
      });
      setData(response);
      setFeedback(t("Создано элементов: {count}.", { count: response.items.length }));
      setObjective("");
      router.push(contentPlanPathFromGeneratedResponse(response) || "/content-plan");
    } catch (value) {
      const reason =
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
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
      setError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
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
        <label>
          <span>{t("Цель недели")}</span>
          <textarea
            onChange={(event) => setObjective(event.target.value)}
            placeholder={copy.goalPlaceholder}
            required
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
          <div className="feedback-actions">
            <button
              className="button button-secondary button-small"
              onClick={() => {
                setError("");
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
      {!loading && (!error || data.items.length) ? (
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
