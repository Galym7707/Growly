"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ContentPlanErrorPanel } from "@/components/content-plan-error";
import { ContentPlanView } from "@/components/content-plan-view";
import { Icon } from "@/components/icons";
import { LoadingState, PageHeader } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanResponse, Draft } from "@/lib/types";

export default function ContentPlanDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<ContentPlanResponse>({
    items: [],
    source: null,
  });
  const [loading, setLoading] = useState(true);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loadErrorDebug, setLoadErrorDebug] = useState<ApiDebugInfo | null>(
    null,
  );
  const [actionErrorDebug, setActionErrorDebug] = useState<ApiDebugInfo | null>(
    null,
  );
  const { locale, t } = useLanguage();
  const copy = contentPlanCopy(locale);

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
      const response = await apiRequest<ContentPlanResponse>(
        `/content-plans/${params.id}`,
      );
      setData(response);
    } catch (value) {
      setLoadErrorDebug(
        apiErrorDebugInfo(value) || { message: "", status: 0, url: "" },
      );
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createDraft(itemId: number) {
    setDraftingId(itemId);
    setError("");
    setActionErrorDebug(null);
    try {
      const response = await apiRequest<{ draft: Draft }>(
        `/content-plan/${itemId}/draft`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      if (response.draft.id) {
        router.push(`/drafts/${response.draft.id}`);
      }
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
        description={t("Созданный план на основе реальных отчётов Growly.")}
        action={
          <Link className="button button-secondary" href="/content-plan">
            <Icon name="chevron" />
            {t("Вернуться к планам")}
          </Link>
        }
      />
      {loading ? <LoadingState /> : null}
      {!loading && loadErrorDebug ? (
        <ContentPlanErrorPanel
          debugInfo={loadErrorDebug}
          manualHref="/content-plan#new-plan"
          onRetry={() => {
            setLoadErrorDebug(null);
            void load();
          }}
        />
      ) : null}
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
        </div>
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
