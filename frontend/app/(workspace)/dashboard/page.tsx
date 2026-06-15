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

  const load = useCallback(async () => {
    setError("");
    try {
      setData(await apiRequest<DashboardData>("/dashboard"));
    } catch (value) {
      setError(value instanceof Error ? value.message : "Неизвестная ошибка");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Рабочая область"
        title="Обзор"
        description="Последние результаты, состояние данных и быстрые действия."
        action={
          <Link className="button button-primary" href="/market-scan">
            <Icon name="plus" />
            Новый анализ
          </Link>
        }
      />
      {!data && !error ? <LoadingState /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {data ? (
        <>
          <section className="overview-strip">
            <div>
              <span>Черновики на согласовании</span>
              <strong>{data.counts.pending_drafts}</strong>
              <Link href="/drafts">Открыть список</Link>
            </div>
            <div>
              <span>Активные источники</span>
              <strong>{data.counts.active_sources}</strong>
              <Link href="/sources">Управлять источниками</Link>
            </div>
            <div>
              <span>Опубликованные материалы</span>
              <strong>{data.counts.published}</strong>
              <span className="muted">По данным Growly</span>
            </div>
            <div>
              <span>Последняя синхронизация Notion</span>
              <strong className="date-value">
                {formatDateTime(data.notion.last_synced_at)}
              </strong>
              <Status value={data.notion.configured ? "active" : "disabled"}>
                {data.notion.configured ? "Настроен" : "Не настроен"}
              </Status>
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Последние результаты</p>
                <h2>Что уже готово</h2>
              </div>
              <Link className="text-link" href="/reports">
                Все отчёты
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
                label="Анализ рынка"
                status={data.latest_market_scan?.status}
                summary={
                  data.latest_market_scan?.summary ||
                  "Анализ ещё не запускался. Укажите нишу и регион."
                }
              />
              <ResultRow
                date={data.latest_competitor_report?.created_at}
                href={
                  data.latest_competitor_report
                    ? `/reports/${data.latest_competitor_report.id}`
                    : "/market-scan"
                }
                label="Конкурентный отчёт"
                status={data.latest_competitor_report?.status}
                summary={
                  data.latest_competitor_report?.summary ||
                  "Появится после сбора и анализа источников."
                }
              />
              <ResultRow
                date={data.latest_content_plan?.created_at}
                href="/content-plan"
                label="Контент-план"
                status={data.latest_content_plan?.status}
                summary={
                  data.latest_content_plan?.topic ||
                  "План ещё не создан. Сначала подготовьте рыночные данные."
                }
              />
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Быстрые действия</p>
                <h2>Продолжить работу</h2>
              </div>
            </div>
            <div className="quick-action-list">
              {quickActions.map((item) => (
                <Link href={item.href} key={item.href}>
                  <Icon name={item.icon} />
                  <div>
                    <strong>{item.title}</strong>
                    <span>{item.text}</span>
                  </div>
                  <Icon name="arrow" />
                </Link>
              ))}
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Согласование</p>
                <h2>Черновики в работе</h2>
              </div>
              <Link className="text-link" href="/drafts">
                Все черновики
                <Icon name="chevron" />
              </Link>
            </div>
            {data.drafts_waiting.length ? (
              <div className="compact-table">
                {data.drafts_waiting.map((draft) => (
                  <Link href="/drafts" key={draft.id}>
                    <span>{draft.title || `Черновик ${draft.id}`}</span>
                    <span>{draft.channel || "Канал не указан"}</span>
                    <Status value={draft.status}>{draft.status}</Status>
                    <span>{formatDate(draft.updated_at)}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="inline-empty">
                Нет черновиков, ожидающих согласования.
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
}: {
  label: string;
  summary: string;
  date?: string;
  status?: string;
  href: string;
}) {
  return (
    <Link href={href}>
      <div>
        <span className="result-label">{label}</span>
        <strong>{summary}</strong>
      </div>
      <div className="result-meta">
        {status ? <Status value={status}>{status}</Status> : null}
        <span>{formatDate(date)}</span>
        <Icon name="arrow" />
      </div>
    </Link>
  );
}
