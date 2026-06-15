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
import type { ContentPlanItem, Draft } from "@/lib/types";

export default function ContentPlanPage() {
  const [items, setItems] = useState<ContentPlanItem[]>([]);
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: ContentPlanItem[] }>(
        "/content-plan",
      );
      setItems(response.items);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
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
      setFeedback(`Создано элементов: ${response.items.length}.`);
      setObjective("");
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
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
      setFeedback(
        `Черновик «${response.draft.title || response.draft.id}» создан.`,
      );
      await load();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    } finally {
      setDraftingId(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Планирование"
        title="Контент-план"
        description="Темы, форматы и задачи на неделю на основе сохранённых источников."
      />
      <form className="form-panel" onSubmit={generate}>
        <h2>Новый план</h2>
        <p>
          Укажите бизнес-цель на неделю. Growly использует последние отчёты и
          материалы источников.
        </p>
        <label>
          <span>Цель недели</span>
          <textarea
            onChange={(event) => setObjective(event.target.value)}
            placeholder="Например: объяснить ценность услуги и получить заявки на консультацию"
            required
            value={objective}
          />
        </label>
        <div className="form-actions">
          <button className="button button-primary" disabled={generating}>
            <Icon name={generating ? "sync" : "book"} />
            {generating ? "Формируем план" : "Создать план"}
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
            <p className="eyebrow">Календарь</p>
            <h2>Запланированные материалы</h2>
          </div>
          <span className="muted">Всего: {items.length}</span>
        </div>
        {loading ? <LoadingState /> : null}
        {!loading && error && !items.length ? (
          <ErrorState message={error} retry={load} />
        ) : null}
        {!loading && !items.length && !error ? (
          <EmptyState
            icon="book"
            text="Сначала выполните анализ рынка, затем сформируйте цель на неделю."
            title="Контент-план ещё не создан"
          />
        ) : null}
        {items.length ? (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Канал</th>
                  <th>Тема</th>
                  <th>Цель</th>
                  <th>Формат</th>
                  <th>Призыв</th>
                  <th>Источник идеи</th>
                  <th>Статус</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.publish_date)}</td>
                    <td>{item.channel || "Не указан"}</td>
                    <td>{item.topic || "Без темы"}</td>
                    <td>{item.goal || "Не указана"}</td>
                    <td>{item.content_type || "Не указан"}</td>
                    <td>{item.cta || "Не указан"}</td>
                    <td>{item.source_idea || "Не указан"}</td>
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
                          ? "Создаём"
                          : item.status === "drafted"
                            ? "Создан"
                            : "Черновик"}
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
