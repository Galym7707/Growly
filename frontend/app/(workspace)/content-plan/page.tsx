"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
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
import type { ContentPlanItem, Draft } from "@/lib/types";

export default function ContentPlanPage() {
  const [items, setItems] = useState<ContentPlanItem[]>([]);
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const { locale, t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: ContentPlanItem[] }>(
        "/content-plan",
      );
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

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setError("");
    setFeedback("");
    try {
      const response = await apiRequest<{ items: ContentPlanItem[] }>(
        "/content-plan",
        {
          method: "POST",
          body: JSON.stringify({ weekly_objective: objective, business: {} }),
        },
      );
      setItems(response.items);
      setFeedback(t("Создано элементов: {count}.", { count: response.items.length }));
      setObjective("");
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
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
        { method: "POST", body: "{}" },
      );
      setFeedback(t("Черновик «{name}» создан.", {
        name: response.draft.title || response.draft.id,
      }));
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setDraftingId(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Планирование")}
        title={t("Контент-план")}
        description={t("Темы, форматы и задачи на неделю на основе сохранённых источников.")}
      />
      <form className="form-panel" onSubmit={generate}>
        <h2>{t("Новый план")}</h2>
        <p>
          {t("Укажите бизнес-цель на неделю. Growly использует последние отчёты и материалы источников.")}
        </p>
        <label>
          <span>{t("Цель недели")}</span>
          <textarea
            onChange={(event) => setObjective(event.target.value)}
            placeholder={t("Например: объяснить ценность услуги и получить заявки на консультацию")}
            required
            value={objective}
          />
        </label>
        <div className="form-actions">
          <button className="button button-primary" disabled={generating}>
            <Icon name={generating ? "sync" : "book"} />
            {t(generating ? "Формируем план" : "Создать план")}
          </button>
        </div>
      </form>
      {error ? <div className="feedback feedback-error">{error}</div> : null}
      {feedback ? (
        <div className="feedback feedback-success">{feedback}</div>
      ) : null}

      <section className="workspace-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{t("Календарь")}</p>
            <h2>{t("Запланированные материалы")}</h2>
          </div>
          <span className="muted">{t("Всего: {count}", { count: items.length })}</span>
        </div>
        {loading ? <LoadingState /> : null}
        {!loading && error && !items.length ? (
          <ErrorState message={error} retry={load} />
        ) : null}
        {!loading && !items.length && !error ? (
          <EmptyState
            icon="book"
            text={t("Сначала выполните анализ рынка, затем сформируйте цель на неделю.")}
            title={t("Контент-план ещё не создан")}
          />
        ) : null}
        {items.length ? (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("Дата")}</th>
                  <th>{t("Канал")}</th>
                  <th>{t("Тема")}</th>
                  <th>{t("Цель")}</th>
                  <th>{t("Формат")}</th>
                  <th>{t("Призыв")}</th>
                  <th>{t("Источник идеи")}</th>
                  <th>{t("Статус")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.publish_date, locale)}</td>
                    <td>{item.channel || t("Не указан")}</td>
                    <td>{item.topic || t("Без темы")}</td>
                    <td>{item.goal || t("Не указана")}</td>
                    <td>{item.content_type || t("Не указан")}</td>
                    <td>{item.cta || t("Не указан")}</td>
                    <td>{item.source_idea || t("Не указан")}</td>
                    <td>
                      <Status value={item.status}>{item.status}</Status>
                    </td>
                    <td>
                      <button
                        className="button button-secondary button-small"
                        disabled={
                          draftingId === item.id || item.status === "drafted"
                        }
                        onClick={() => createDraft(item.id)}
                        type="button"
                      >
                        {draftingId === item.id
                          ? t("Создаём")
                          : item.status === "drafted"
                            ? t("Создан")
                            : t("Черновик")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
