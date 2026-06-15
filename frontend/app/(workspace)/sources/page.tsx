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
import type { Source } from "@/lib/types";

export default function SourcesPage() {
  const [items, setItems] = useState<Source[]>([]);
  const [mode, setMode] = useState<"discover" | "manual">("discover");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [niche, setNiche] = useState("");
  const [region, setRegion] = useState("Казахстан");
  const [platforms, setPlatforms] = useState("website, telegram, instagram");
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Source[] }>("/sources");
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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      if (mode === "discover") {
        const response = await apiRequest<{ items: Source[] }>(
          "/sources/discover",
          {
            method: "POST",
            body: JSON.stringify({
              niche,
              region,
              platforms: platforms
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
            }),
          },
        );
        setFeedback(`Найдено кандидатов: ${response.items.length}.`);
      } else {
        await apiRequest("/sources", {
          method: "POST",
          body: JSON.stringify({
            name,
            url,
            source_type: "website",
            category: "competitor",
            priority: "medium",
            check_frequency: "weekly",
          }),
        });
        setFeedback("Источник добавлен.");
        setName("");
        setUrl("");
      }
      await load();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function monitor() {
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      const response = await apiRequest<{ items_saved: number }>(
        "/sources/monitor",
        { method: "POST", body: "{}" },
      );
      setFeedback(`Сохранено новых материалов: ${response.items_saved}.`);
      await load();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Данные"
        title="Источники"
        description="Публичные сайты и каналы, которые Growly использует как рыночные свидетельства."
        action={
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={monitor}
            type="button"
          >
            <Icon name="sync" />
            Проверить активные
          </button>
        }
      />
      <form className="form-panel" onSubmit={submit}>
        <div className="list-toolbar">
          <div>
            <h2>{mode === "discover" ? "Найти источники" : "Добавить вручную"}</h2>
            <p>
              {mode === "discover"
                ? "Tavily ищет только публично доступные страницы."
                : "Добавьте известный вам официальный источник."}
            </p>
          </div>
          <select
            aria-label="Способ добавления"
            onChange={(event) =>
              setMode(event.target.value as "discover" | "manual")
            }
            value={mode}
          >
            <option value="discover">Поиск</option>
            <option value="manual">Вручную</option>
          </select>
        </div>
        {mode === "discover" ? (
          <div className="form-grid">
            <label>
              <span>Ниша</span>
              <input
                onChange={(event) => setNiche(event.target.value)}
                required
                value={niche}
              />
            </label>
            <label>
              <span>Регион</span>
              <input
                onChange={(event) => setRegion(event.target.value)}
                required
                value={region}
              />
            </label>
            <label className="full">
              <span>Платформы через запятую</span>
              <input
                onChange={(event) => setPlatforms(event.target.value)}
                value={platforms}
              />
            </label>
          </div>
        ) : (
          <div className="form-grid">
            <label>
              <span>Название</span>
              <input
                onChange={(event) => setName(event.target.value)}
                required
                value={name}
              />
            </label>
            <label>
              <span>URL</span>
              <input
                onChange={(event) => setUrl(event.target.value)}
                required
                type="url"
                value={url}
              />
            </label>
          </div>
        )}
        <div className="form-actions">
          <button className="button button-primary" disabled={busy}>
            <Icon name={busy ? "sync" : "plus"} />
            {busy
              ? "Выполняется"
              : mode === "discover"
                ? "Найти кандидатов"
                : "Добавить источник"}
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
            <p className="eyebrow">Реестр</p>
            <h2>Сохранённые источники</h2>
          </div>
          <span className="muted">Всего: {items.length}</span>
        </div>
        {loading ? <LoadingState /> : null}
        {!loading && error && !items.length ? (
          <ErrorState message={error} retry={load} />
        ) : null}
        {!loading && !items.length && !error ? (
          <EmptyState
            icon="source"
            text="Добавьте известный источник или найдите публичные страницы по нише."
            title="Источников пока нет"
          />
        ) : null}
        {items.length ? (
          <div className="source-list">
            {items.map((source) => (
              <article className="source-item" key={source.id}>
                <div>
                  <h3>{source.name}</h3>
                  {source.url ? (
                    <a href={source.url} rel="noreferrer" target="_blank">
                      {source.url}
                    </a>
                  ) : (
                    <p>URL не указан</p>
                  )}
                </div>
                <span>{source.type || "Не указан"}</span>
                <span>{formatDate(source.last_checked_at)}</span>
                <Status value={source.status}>{source.status}</Status>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
