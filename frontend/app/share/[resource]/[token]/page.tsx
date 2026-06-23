"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { ApiError, apiRequest, formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

type SharedResource = Record<string, unknown>;

type ShareResponse = {
  resource_type: string;
  access_level: string;
  resource: SharedResource | null;
};

export default function SharePage() {
  const params = useParams<{ resource: string; token: string }>();
  const token = params.token;
  const { locale, t } = useLanguage();

  const [data, setData] = useState<ShareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [needsPassword, setNeedsPassword] = useState(false);
  const [password, setPassword] = useState("");

  const load = useCallback(
    async (pw?: string) => {
      setLoading(true);
      setError("");
      try {
        const query = pw ? `?password=${encodeURIComponent(pw)}` : "";
        const response = await apiRequest<ShareResponse>(
          `/share-links/${encodeURIComponent(token)}${query}`,
        );
        setData(response);
        setNeedsPassword(false);
      } catch (value) {
        if (value instanceof ApiError && value.status === 401) {
          setNeedsPassword(true);
        } else {
          setError(
            value instanceof Error ? t(value.message) : t("Ссылка недоступна."),
          );
        }
      } finally {
        setLoading(false);
      }
    },
    [token, t],
  );

  useEffect(() => {
    void load();
  }, [load]);

  function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load(password);
  }

  return (
    <main className="share-page">
      <header className="share-header">
        <Logo />
        <LanguageSwitcher compact />
      </header>

      <div className="share-body">
        {loading ? <p className="muted">{t("Загрузка данных")}…</p> : null}

        {!loading && needsPassword ? (
          <form className="share-password" onSubmit={submitPassword}>
            <h2>{t("Ссылка защищена паролем")}</h2>
            <label>
              <span>{t("Пароль")}</span>
              <input
                autoFocus
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
            <button className="button button-primary" type="submit">
              {t("Открыть")}
            </button>
          </form>
        ) : null}

        {!loading && error ? (
          <div className="share-empty">
            <p className="feedback feedback-error">{error}</p>
            <Link className="text-link" href="/">
              {t("Вернуться на главную")}
              <Icon name="arrow" />
            </Link>
          </div>
        ) : null}

        {!loading && data?.resource ? (
          <article className="share-card">
            <SharedView
              type={data.resource_type}
              resource={data.resource}
              locale={locale}
              t={t}
            />
            <footer className="share-foot muted">
              {t("Просмотр только для чтения · Growly")}
            </footer>
          </article>
        ) : null}
      </div>
    </main>
  );
}

function SharedView({
  type,
  resource,
  locale,
  t,
}: {
  type: string;
  resource: SharedResource;
  locale: "ru" | "en" | "kk";
  t: (key: string) => string;
}) {
  const str = (key: string): string => {
    const value = resource[key];
    return typeof value === "string" ? value : "";
  };

  if (type === "report") {
    return (
      <>
        <p className="eyebrow">{t("Отчёт")}</p>
        <h1>{str("title") || t("Отчёт")}</h1>
        {str("summary") ? <p className="share-summary">{str("summary")}</p> : null}
        {str("body") ? <div className="share-text">{str("body")}</div> : null}
        <p className="muted">{formatDate(str("created_at"), locale)}</p>
      </>
    );
  }
  if (type === "draft") {
    return (
      <>
        <p className="eyebrow">{t("Черновик")}</p>
        <h1>{str("title") || t("Черновик")}</h1>
        {str("channel") ? <p className="muted">{str("channel")}</p> : null}
        <div className="share-text">{str("text")}</div>
      </>
    );
  }
  if (type === "content_plan") {
    return (
      <>
        <p className="eyebrow">{t("Контент-план")}</p>
        <h1>{str("topic") || t("Тема")}</h1>
        <dl className="share-meta">
          <div>
            <dt>{t("Канал")}</dt>
            <dd>{str("channel") || "—"}</dd>
          </div>
          <div>
            <dt>{t("Формат")}</dt>
            <dd>{str("content_type") || "—"}</dd>
          </div>
          <div>
            <dt>{t("Цель")}</dt>
            <dd>{str("goal") || "—"}</dd>
          </div>
          <div>
            <dt>CTA</dt>
            <dd>{str("cta") || "—"}</dd>
          </div>
        </dl>
      </>
    );
  }
  return <p className="muted">{t("Просмотр только для чтения · Growly")}</p>;
}
