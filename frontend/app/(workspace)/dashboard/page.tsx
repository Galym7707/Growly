"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import { apiRequest, formatDate, formatDateTime } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { DashboardData } from "@/lib/types";

const quickActions = [
  {
    href: "/market-scan",
    title: "Новый анализ рынка",
    text: "Собрать и сохранить публичные источники.",
    icon: "market" as const,
  },
  {
    href: "/content-plan",
    title: "Создать контент-план",
    text: "Сформировать недельный план на основе данных.",
    icon: "book" as const,
  },
  {
    href: "/chat?action=create_post",
    title: "Подготовить пост",
    text: "Передать бриф и получить черновик.",
    icon: "draft" as const,
  },
];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const { locale, t } = useLanguage();

  const load = useCallback(async () => {
    setError("");
    try {
      setData(await apiRequest<DashboardData>("/dashboard"));
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Рабочая область")}
        title={t("Обзор")}
        description={t("Последние результаты, состояние данных и быстрые действия.")}
        action={
          <Link className="button button-primary" href="/market-scan">
            <Icon name="plus" />
            {t("Новый анализ")}
          </Link>
        }
      />
      {!data && !error ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {data ? (
        <>
          <section className="overview-strip">
            <div>
              <span>{t("Черновики на согласовании")}</span>
              <strong>{data.counts.pending_drafts}</strong>
              <Link href="/drafts">{t("Открыть список")}</Link>
            </div>
            <div>
              <span>{t("Активные источники")}</span>
              <strong>{data.counts.active_sources}</strong>
              <Link href="/sources">{t("Управлять источниками")}</Link>
            </div>
            <div>
              <span>{t("Опубликованные материалы")}</span>
              <strong>{data.counts.published}</strong>
              <span className="muted">{t("По данным Growly")}</span>
            </div>
            <div>
              <span>{t("Последняя синхронизация Notion")}</span>
              <strong className="date-value">
                {formatDateTime(data.notion.last_synced_at, locale)}
              </strong>
              <Status value={data.notion.configured ? "active" : "disabled"}>
                {t(data.notion.configured ? "Настроен" : "Не настроен")}
              </Status>
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Последние результаты")}</p>
                <h2>{t("Что уже готово")}</h2>
              </div>
              <Link className="text-link" href="/reports">
                {t("Все отчёты")}
                <Icon name="chevron" />
              </Link>
            </div>
            <div className="result-list">
              <ResultRow
                date={data.latest_market_scan?.created_at}
                href={
                  data.latest_market_scan
                    ? `/reports/${data.latest_market_scan.id}`
                    : "/market-scan"
                }
                label={t("Анализ рынка")}
                locale={locale}
                status={data.latest_market_scan?.status}
                summary={
                  data.latest_market_scan?.summary ||
                  t("Анализ ещё не запускался. Укажите нишу и регион.")
                }
              />
              <ResultRow
                date={data.latest_competitor_report?.created_at}
                href={
                  data.latest_competitor_report
                    ? `/reports/${data.latest_competitor_report.id}`
                    : "/market-scan"
                }
                label={t("Конкурентный отчёт")}
                locale={locale}
                status={data.latest_competitor_report?.status}
                summary={
                  data.latest_competitor_report?.summary ||
                  t("Появится после сбора и анализа источников.")
                }
              />
              <ResultRow
                date={data.latest_content_plan?.created_at}
                href="/content-plan"
                label={t("Контент-план")}
                locale={locale}
                status={data.latest_content_plan?.status}
                summary={
                  data.latest_content_plan?.topic ||
                  t("План ещё не создан. Сначала подготовьте рыночные данные.")
                }
              />
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Быстрые действия")}</p>
                <h2>{t("Продолжить работу")}</h2>
              </div>
            </div>
            <div className="quick-action-list">
              {quickActions.map((item) => (
                <Link href={item.href} key={item.href}>
                  <Icon name={item.icon} />
                  <div>
                    <strong>{t(item.title)}</strong>
                    <span>{t(item.text)}</span>
                  </div>
                  <Icon name="arrow" />
                </Link>
              ))}
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Согласование")}</p>
                <h2>{t("Черновики в работе")}</h2>
              </div>
              <Link className="text-link" href="/drafts">
                {t("Все черновики")}
                <Icon name="chevron" />
              </Link>
            </div>
            {data.drafts_waiting.length ? (
              <div className="compact-table">
                {data.drafts_waiting.map((draft) => (
                  <Link href="/drafts" key={draft.id}>
                    <span>{draft.title || `${t("Черновик")} ${draft.id}`}</span>
                    <span>{draft.channel || t("Канал не указан")}</span>
                    <Status value={draft.status}>{draft.status}</Status>
                    <span>{formatDate(draft.updated_at, locale)}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="inline-empty">
                {t("Нет черновиков, ожидающих согласования.")}
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

function ResultRow({
  label,
  summary,
  date,
  status,
  href,
  locale,
}: {
  label: string;
  summary: string;
  date?: string;
  status?: string;
  href: string;
  locale: "ru" | "en" | "kk";
}) {
  return (
    <Link href={href}>
      <div>
        <span className="result-label">{label}</span>
        <strong>{summary}</strong>
      </div>
      <div className="result-meta">
        {status ? <Status value={status}>{status}</Status> : null}
        <span>{formatDate(date, locale)}</span>
        <Icon name="arrow" />
      </div>
    </Link>
  );
}
