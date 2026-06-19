"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { activeContextTopic } from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanResponse, Draft } from "@/lib/types";

type Mode = "analysis" | "manual";

export default function CreatePostPage() {
  const router = useRouter();
  const { locale, t } = useLanguage();
  const { active } = useActiveContext();
  const activeTopic = activeContextTopic(active);

  const [hasPlan, setHasPlan] = useState(false);
  const [mode, setMode] = useState<Mode | null>(null);
  const [brief, setBrief] = useState("");
  const [channel, setChannel] = useState("Telegram");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const loadPlan = useCallback(async () => {
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans");
      setHasPlan(response.items.length > 0);
    } catch {
      setHasPlan(false);
    }
  }, []);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  async function generate(text: string) {
    const cleaned = text.trim();
    if (cleaned.length < 10) {
      setError(t("Опишите задачу подробнее (минимум 10 символов)."));
      return;
    }
    setGenerating(true);
    setError("");
    try {
      const response = await apiRequest<{ draft: Draft }>("/create-post", {
        method: "POST",
        body: JSON.stringify({
          brief: cleaned,
          channel: channel.trim() || "Telegram",
          language: locale,
        }),
      });
      void response;
      router.push("/drafts");
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
      setGenerating(false);
    }
  }

  function generateFromAnalysis() {
    if (!active) return;
    const topic = activeTopic || t("последний анализ рынка");
    const region = active.region ? `, регион: ${active.region}` : "";
    const composed = t(
      "Создай продающий пост для канала {channel} на основе последнего анализа рынка. Ниша: {topic}{region}. Используй боли клиентов и офферы из анализа, добавь конкретный призыв к действию.",
      { channel: channel.trim() || "Telegram", topic, region },
    );
    void generate(composed);
  }

  function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void generate(brief);
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Контент")}
        title={t("Создать пост")}
        description={t("Подготовьте пост на основе анализа, контент-плана или вручную.")}
      />

      <div className="post-options">
        <button
          className="post-option"
          disabled={!active || generating}
          onClick={generateFromAnalysis}
          type="button"
        >
          <Icon name="market" />
          <div>
            <strong>{t("Создать пост по последнему анализу")}</strong>
            <span>
              {active && activeTopic
                ? t("На основе анализа: {topic}", { topic: activeTopic })
                : t("Сначала выполните анализ рынка.")}
            </span>
          </div>
          <Icon name="arrow" />
        </button>

        <Link
          aria-disabled={!hasPlan}
          className={`post-option${hasPlan ? "" : " post-option-disabled"}`}
          href={hasPlan ? "/content-plan" : "/create-post"}
        >
          <Icon name="book" />
          <div>
            <strong>{t("Создать пост из контент-плана")}</strong>
            <span>
              {hasPlan
                ? t("Откройте план и создайте черновик из выбранной темы.")
                : t("Контент-план ещё не создан.")}
            </span>
          </div>
          <Icon name="arrow" />
        </Link>

        <button
          className={`post-option${mode === "manual" ? " post-option-active" : ""}`}
          onClick={() => setMode(mode === "manual" ? null : "manual")}
          type="button"
        >
          <Icon name="draft" />
          <div>
            <strong>{t("Создать вручную")}</strong>
            <span>{t("Передайте свой бриф и канал.")}</span>
          </div>
          <Icon name="arrow" />
        </button>
      </div>

      {mode === "manual" ? (
        <form className="form-panel" onSubmit={submitManual}>
          <h2>{t("Создать вручную")}</h2>
          <div className="form-grid">
            <label className="full">
              <span>{t("Бриф")}</span>
              <textarea
                onChange={(event) => setBrief(event.target.value)}
                placeholder={t("Передайте подробный бриф, канал и желаемый призыв")}
                required
                value={brief}
              />
            </label>
            <label>
              <span>{t("Канал")}</span>
              <input
                onChange={(event) => setChannel(event.target.value)}
                value={channel}
              />
            </label>
          </div>
          <div className="form-actions">
            <button className="button button-primary" disabled={generating}>
              <Icon name={generating ? "sync" : "draft"} />
              {generating ? t("Формируем пост") : t("Создать пост")}
            </button>
          </div>
        </form>
      ) : null}

      {generating && mode !== "manual" ? (
        <div className="feedback">{t("Формируем пост на сервере...")}</div>
      ) : null}
      {error ? <div className="feedback feedback-error">{error}</div> : null}
    </div>
  );
}
