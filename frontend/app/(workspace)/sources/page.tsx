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
import { apiRequest, formatDate, formatStatusLabel } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
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
  const { locale, t } = useLanguage();

  useEffect(() => {
    setRegion(
      locale === "kk"
        ? "Қазақстан"
        : locale === "en"
          ? "Kazakhstan"
          : "Казахстан",
    );
  }, [locale]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: Source[] }>("/sources");
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
        setFeedback(t("Найдено кандидатов: {count}.", { count: response.items.length }));
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
        setFeedback(t("Источник добавлен."));
        setName("");
        setUrl("");
      }
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
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
      setFeedback(t("Сохранено новых материалов: {count}.", { count: response.items_saved }));
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Данные")}
        title={t("Источники")}
        description={t("Публичные сайты и каналы, которые Growly использует как рыночные свидетельства.")}
        action={
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={monitor}
            type="button"
          >
            <Icon name="sync" />
            {t("Проверить активные")}
          </button>
        }
      />
      <form className="form-panel" onSubmit={submit}>
        <div className="list-toolbar">
          <div>
            <h2>{t(mode === "discover" ? "Найти источники" : "Добавить вручную")}</h2>
            <p>
              {mode === "discover"
                ? t("Tavily ищет только публично доступные страницы.")
                : t("Добавьте известный вам официальный источник.")}
            </p>
          </div>
          <select
            aria-label={t("Способ добавления")}
            onChange={(event) =>
              setMode(event.target.value as "discover" | "manual")
            }
            value={mode}
          >
            <option value="discover">{t("Поиск")}</option>
            <option value="manual">{t("Вручную")}</option>
          </select>
        </div>
        {mode === "discover" ? (
          <div className="form-grid">
            <label>
              <span>{t("Ниша")}</span>
              <input
                onChange={(event) => setNiche(event.target.value)}
                required
                value={niche}
              />
            </label>
            <label>
              <span>{t("Регион")}</span>
              <input
                onChange={(event) => setRegion(event.target.value)}
                required
                value={region}
              />
            </label>
            <label className="full">
              <span>{t("Платформы через запятую")}</span>
              <input
                onChange={(event) => setPlatforms(event.target.value)}
                value={platforms}
              />
            </label>
          </div>
        ) : (
          <div className="form-grid">
            <label>
              <span>{t("Название")}</span>
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
              ? t("Выполняется")
              : mode === "discover"
                ? t("Найти кандидатов")
                : t("Добавить источник")}
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
            <p className="eyebrow">{t("Реестр")}</p>
            <h2>{t("Сохранённые источники")}</h2>
          </div>
          <span className="muted">{t("Всего: {count}", { count: items.length })}</span>
        </div>
        {loading ? <LoadingState /> : null}
        {!loading && error && !items.length ? (
          <ErrorState message={error} retry={load} />
        ) : null}
        {!loading && !items.length && !error ? (
          <EmptyState
            icon="source"
            text={t("Добавьте известный источник или найдите публичные страницы по нише.")}
            title={t("Источников пока нет")}
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
                    <p>{t("URL не указан")}</p>
                  )}
                </div>
                <span>{source.type || t("Не указан")}</span>
                <span>{formatDate(source.last_checked_at, locale)}</span>
                <Status value={source.status}>
                  {formatStatusLabel(source.status, locale)}
                </Status>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
