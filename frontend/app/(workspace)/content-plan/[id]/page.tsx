"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ContentPlanErrorPanel } from "@/components/content-plan-error";
import { ContentPlanView } from "@/components/content-plan-view";
import { Icon } from "@/components/icons";
import { CopyShareLinkButton } from "@/components/team/share-controls";
import { TasksPanel } from "@/components/tasks/tasks-panel";
import { LoadingState, PageHeader } from "@/components/ui";
import { apiErrorDebugInfo, apiRequest, type ApiDebugInfo } from "@/lib/api";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { useLanguage } from "@/lib/i18n";
import type { SocialStatus } from "@/lib/integrations";
import type { ContentPlanItem, ContentPlanResponse, Draft } from "@/lib/types";

export default function ContentPlanDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<ContentPlanResponse>({
    items: [],
    source: null,
  });
  const [social, setSocial] = useState<SocialStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [igModal, setIgModal] = useState<"none" | "not_connected" | "pending">(
    "none",
  );
  const [error, setError] = useState("");
  const [taskingId, setTaskingId] = useState<number | null>(null);
  const [tasksReload, setTasksReload] = useState(0);
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
    if (debugInfo) {
      const message = debugInfo.message.trim();
      if (message && message.toLowerCase() !== "internal server error") {
        return t(message);
      }
      if (debugInfo.status === 429) {
        return t(
          "Генерация временно недоступна: лимит AI-сервиса исчерпан. Попробуйте позже.",
        );
      }
    }
    if (debugInfo && debugInfo.status >= 500) {
      return t("Задачу не удалось выполнить. Сервис временно недоступен.");
    }
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
    // Social status is best-effort; failure should not block the plan.
    try {
      const status = await apiRequest<SocialStatus>(
        "/integrations/social/status?platform=instagram",
      );
      setSocial(status);
    } catch {
      setSocial(null);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  function targetsInstagram(item: ContentPlanItem): boolean {
    return (item.channel || "").toLowerCase().includes("instagram");
  }

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

  function openDraft(item: ContentPlanItem) {
    if (item.draft_id) router.push(`/drafts/${item.draft_id}`);
  }

  async function createTaskFromItem(item: ContentPlanItem) {
    setTaskingId(item.id);
    setError("");
    try {
      await apiRequest("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: item.topic || t("Без темы"),
          source_type: "content_plan",
          source_id: Number(params.id),
          assignee_email: null,
        }),
      });
      setTasksReload((value) => value + 1);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setTaskingId(null);
    }
  }

  function goToDraftWithIntent(item: ContentPlanItem, intent: "publish" | "schedule") {
    if (targetsInstagram(item)) {
      const state = social?.state ?? "not_connected";
      if (state === "pending" || state === "in_progress") {
        setIgModal("pending");
        return;
      }
      if (state !== "connected") {
        setIgModal("not_connected");
        return;
      }
    }
    if (item.draft_id) {
      router.push(`/drafts/${item.draft_id}?intent=${intent}`);
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

      {!loading && !loadErrorDebug ? (
        <div className="plan-instruction">
          <Icon name="book" />
          <p>
            {t(
              "Выберите тему из плана и нажмите «Создать черновик», «Опубликовать» или «Запланировать». Для автопостинга в Instagram сначала подключите Blotato в разделе «Интеграции».",
            )}
          </p>
        </div>
      ) : null}

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
          onOpenDraft={openDraft}
          onPublish={(item) => goToDraftWithIntent(item, "publish")}
          onSchedule={(item) => goToDraftWithIntent(item, "schedule")}
          onCreateTask={createTaskFromItem}
          taskingId={taskingId}
          source={data.source}
        />
      ) : null}

      {!loading && !loadErrorDebug && Number.isFinite(Number(params.id)) ? (
        <>
          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Команда")}</p>
                <h2>{t("Что делать дальше")}</h2>
              </div>
              <CopyShareLinkButton
                className="button button-secondary button-small"
                resourceType="content_plan"
                resourceId={Number(params.id)}
              />
            </div>
            <TasksPanel
              reloadSignal={tasksReload}
              source={{
                source_type: "content_plan",
                source_id: Number(params.id),
              }}
            />
          </section>
        </>
      ) : null}

      {igModal !== "none" ? (
        <div className="modal-backdrop" onClick={() => setIgModal("none")}>
          <div
            className="modal-card"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            {igModal === "pending" ? (
              <>
                <h2>{t("Заявка уже отправлена")}</h2>
                <p className="muted">
                  {t("Администратор подключит ваш Instagram через безопасный OAuth-flow. После подключения публикация станет доступна.")}
                </p>
                <div className="form-actions">
                  <button
                    className="button button-secondary"
                    onClick={() => setIgModal("none")}
                    type="button"
                  >
                    {t("Закрыть")}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2>{t("Instagram не подключен")}</h2>
                <p className="muted">
                  {t("Чтобы Growly мог автоматически публиковать посты, отправьте заявку на подключение Instagram. Пароль не нужен: подключение проходит через официальный OAuth.")}
                </p>
                <div className="form-actions">
                  <Link className="button button-primary" href="/settings/integrations">
                    {t("Перейти в Интеграции")}
                  </Link>
                  <button
                    className="button button-secondary"
                    onClick={() => setIgModal("none")}
                    type="button"
                  >
                    {t("Отмена")}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
