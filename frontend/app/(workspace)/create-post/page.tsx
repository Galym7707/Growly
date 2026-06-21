"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { activeContextTopic } from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import {
  contentPlanPathFromResponse,
  latestContentPlanPath,
} from "@/lib/content-plan";
import { useLanguage } from "@/lib/i18n";
import { PUBLISH_PLATFORMS, type SocialStatus } from "@/lib/integrations";
import type { ContentPlanResponse, Draft } from "@/lib/types";

type Mode = "analysis" | "manual";

export default function CreatePostPage() {
  return (
    <Suspense fallback={<div className="workspace-page" />}>
      <CreatePostContent />
    </Suspense>
  );
}

function CreatePostContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reportIdParam = searchParams.get("reportId");
  const { locale, t } = useLanguage();
  const { active, loadActiveReport } = useActiveContext();
  const activeTopic = activeContextTopic(active);

  const [latestPlanPath, setLatestPlanPath] = useState<string | null>(null);
  const [social, setSocial] = useState<SocialStatus | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [brief, setBrief] = useState("");
  const [channel, setChannel] = useState("telegram");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const hydratedParam = useRef<string | null>(null);

  useEffect(() => {
    if (!reportIdParam || !/^\d+$/.test(reportIdParam)) return;
    if (hydratedParam.current === reportIdParam) return;
    if (active && active.report_id === Number(reportIdParam)) {
      hydratedParam.current = reportIdParam;
      return;
    }
    hydratedParam.current = reportIdParam;
    void loadActiveReport(Number(reportIdParam));
  }, [reportIdParam, active, loadActiveReport]);

  const loadPlan = useCallback(async () => {
    try {
      const response = await apiRequest<ContentPlanResponse>("/content-plans");
      setLatestPlanPath(
        contentPlanPathFromResponse(response) ||
          latestContentPlanPath(response.items),
      );
    } catch {
      setLatestPlanPath(null);
    }
  }, []);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  useEffect(() => {
    let active = true;
    void apiRequest<SocialStatus>(
      "/integrations/social/status?platform=instagram",
    )
      .then((status) => {
        if (active) setSocial(status);
      })
      .catch(() => {
        if (active) setSocial(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const instagramSelected = channel === "instagram";
  const instagramState = social?.state ?? "not_connected";

  const selectedChannel =
    PUBLISH_PLATFORMS.find((platform) => platform.slug === channel)?.label ||
    channel;
  const hasPlan = Boolean(latestPlanPath);

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
          channel: selectedChannel,
          language: locale,
        }),
      });
      router.push(`/drafts/${response.draft.id}`);
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
      { channel: selectedChannel, topic, region },
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

      <label className="post-channel-field">
        <span>{t("Канал")}</span>
        <select
          onChange={(event) => setChannel(event.target.value)}
          value={channel}
        >
          {PUBLISH_PLATFORMS.map((platform) => (
            <option key={platform.slug} value={platform.slug}>
              {platform.label}
            </option>
          ))}
        </select>
      </label>

      {instagramSelected && instagramState === "not_connected" ? (
        <div className="feedback feedback-warning create-post-warning">
          <span>
            {t("Instagram автопостинг не подключен. Отправьте заявку на подключение в Интеграциях.")}
          </span>
          <Link className="button button-secondary button-small" href="/settings/integrations">
            {t("Перейти в Интеграции")}
          </Link>
        </div>
      ) : null}
      {instagramSelected && (instagramState === "pending" || instagramState === "in_progress") ? (
        <div className="feedback feedback-warning">
          {t("Заявка на подключение Instagram уже отправлена. После подключения вы сможете публиковать посты автоматически.")}
        </div>
      ) : null}
      {instagramSelected && instagramState === "connected" ? (
        <div className="feedback feedback-success">
          {t("Instagram подключен. Пост можно опубликовать или запланировать.")}
        </div>
      ) : null}

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
          href={latestPlanPath || "/create-post"}
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
