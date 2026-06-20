"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import { apiRequest, formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Draft } from "@/lib/types";

type DraftAction = "approve" | "reject" | "regenerate" | "sync_notion";

export default function DraftsPage() {
  const [items, setItems] = useState<Draft[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const { locale, t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Draft[] }>("/drafts");
      setItems(response.items);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(
    () =>
      filter === "all"
        ? items
        : items.filter((item) => item.status === filter),
    [filter, items],
  );

  async function act(id: number, action: DraftAction) {
    setBusy(id);
    setError("");
    try {
      const response = await apiRequest<{ draft: Draft }>(`/drafts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ action }),
      });
      setItems((current) =>
        current.map((item) => (item.id === id ? response.draft : item)),
      );
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Согласование")}
        title={t("Черновики")}
        description={t("Версии материалов, статусы согласования и сохранение в Notion.")}
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {!loading ? (
        <>
          <div className="list-toolbar">
            <select
              aria-label={t("Фильтр статуса")}
              onChange={(event) => setFilter(event.target.value)}
              value={filter}
            >
              <option value="all">{t("Все статусы")}</option>
              <option value="pending">{t("На согласовании")}</option>
              <option value="approved">{t("Согласованные")}</option>
              <option value="rejected">{t("Отклонённые")}</option>
              <option value="published">{t("Опубликованные")}</option>
            </select>
            <span className="muted">{t("Показано: {count}", { count: visible.length })}</span>
          </div>
          {visible.length ? (
            <div className="draft-list">
              {visible.map((draft) => (
                <article className="draft-item" key={draft.id}>
                  <div>
                    <h3>{draft.title || `${t("Черновик")} ${draft.id}`}</h3>
                    <p>
                      {draft.channel || t("Канал не указан")} ·{" "}
                      {t("версия {version}", { version: draft.version })}
                    </p>
                    <div className="item-meta">
                      <Status value={draft.status}>{draft.status}</Status>
                      <span className="muted">{formatDate(draft.updated_at, locale)}</span>
                      <span className="muted">
                        {draft.notion_synced
                          ? t("Сохранён в Notion")
                          : t("Не сохранён в Notion")}
                      </span>
                    </div>
                    <div className="item-actions">
                      <Link
                        className="button button-secondary"
                        href={`/drafts/${draft.id}`}
                      >
                        <Icon name="arrow" />
                        {t("Открыть и опубликовать")}
                      </Link>
                      <button
                        className="button button-primary"
                        disabled={busy === draft.id || draft.status === "published"}
                        onClick={() => act(draft.id, "approve")}
                        type="button"
                      >
                        <Icon name="check" />
                        {t("Согласовать")}
                      </button>
                      <button
                        className="button button-secondary"
                        disabled={busy === draft.id || draft.status === "published"}
                        onClick={() => act(draft.id, "regenerate")}
                        type="button"
                      >
                        <Icon name="sync" />
                        {t("Новая версия")}
                      </button>
                      <button
                        className="button button-secondary"
                        disabled={busy === draft.id}
                        onClick={() => act(draft.id, "sync_notion")}
                        type="button"
                      >
                        <Icon name="notion" />
                        {t("В Notion")}
                      </button>
                      <button
                        className="button button-secondary"
                        disabled={busy === draft.id || draft.status === "published"}
                        onClick={() => act(draft.id, "reject")}
                        type="button"
                      >
                        {t("Отклонить")}
                      </button>
                    </div>
                  </div>
                  <div className="draft-text">{draft.text}</div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              action={t("Создать пост")}
              href="/chat?action=create_post"
              icon="draft"
              text={t("Черновики появятся после генерации поста или создания материала из контент-плана.")}
              title={t("Черновиков пока нет")}
            />
          )}
        </>
      ) : null}
    </div>
  );
}
