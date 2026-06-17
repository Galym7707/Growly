"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ContentPlanView } from "@/components/content-plan-view";
import { Icon } from "@/components/icons";
import { ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
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
  const { locale, t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<ContentPlanResponse>(
        `/content-plans/${params.id}`,
      );
      setData(response);
    } catch (value) {
      setError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
    } finally {
      setLoading(false);
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createDraft(itemId: number) {
    setDraftingId(itemId);
    setError("");
    try {
      const response = await apiRequest<{ draft: Draft }>(
        `/content-plan/${itemId}/draft`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      if (response.draft.id) {
        router.push("/drafts");
      }
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
        description={t("Созданный план на основе реальных отчётов Growly.")}
        action={
          <Link className="button button-secondary" href="/content-plan">
            <Icon name="chevron" />
            {t("Вернуться к планам")}
          </Link>
        }
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {!loading && !error ? (
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
