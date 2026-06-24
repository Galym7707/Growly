"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { Status } from "@/components/ui";
import { formatDate } from "@/lib/api";
import {
  contentPlanSourceText,
  formatContentType,
  sourceDisplay,
} from "@/lib/content-plan";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanItem, ContentPlanSource } from "@/lib/types";

type PlanItemState =
  | "not_created"
  | "draft"
  | "scheduled"
  | "published"
  | "error";

type Props = {
  draftingId?: number | null;
  items: ContentPlanItem[];
  onCreateDraft?: (itemId: number) => void;
  onOpenDraft?: (item: ContentPlanItem) => void;
  onPublish?: (item: ContentPlanItem) => void;
  onSchedule?: (item: ContentPlanItem) => void;
  onCreateTask?: (item: ContentPlanItem) => void;
  taskingId?: number | null;
  source?: ContentPlanSource | null;
};

function itemState(item: ContentPlanItem): PlanItemState {
  const status = (item.status || "").toLowerCase();
  if (status === "published") return "published";
  if (status === "scheduled") return "scheduled";
  if (status === "error" || status === "failed") return "error";
  if (item.draft_id || status === "drafted" || status === "draft") {
    // A plan item starts as "draft" in the DB but only has a real draft once
    // generated. Treat it as a draft only when a draft actually exists.
    return item.draft_id ? "draft" : "not_created";
  }
  return "not_created";
}

export function ContentPlanView({
  draftingId = null,
  items,
  onCreateDraft,
  onOpenDraft,
  onPublish,
  onSchedule,
  onCreateTask,
  taskingId = null,
  source = null,
}: Props) {
  const { locale, t } = useLanguage();
  const copy = contentPlanCopy(locale);
  const hasActions = Boolean(
    onCreateDraft || onOpenDraft || onPublish || onSchedule || onCreateTask,
  );

  const stateLabels: Record<PlanItemState, string> = {
    not_created: "Не создан",
    draft: "Черновик",
    scheduled: "Запланирован",
    published: "Опубликован",
    error: "Ошибка",
  };
  const stateBadge: Record<PlanItemState, string> = {
    not_created: "pending",
    draft: "draft",
    scheduled: "scheduled",
    published: "active",
    error: "failed",
  };

  return (
    <section className="workspace-section content-plan-results">
      <div className="plan-source">
        <p className="eyebrow">{copy.basedOn}</p>
        <p>{contentPlanSourceText(source, locale)}</p>
      </div>

      <div className="section-heading">
        <div>
          <p className="eyebrow">{copy.newPlan}</p>
          <h2>{copy.count(items.length)}</h2>
        </div>
      </div>

      {items.length ? (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{copy.table.date}</th>
                <th>{copy.table.channel}</th>
                <th>{copy.table.topic}</th>
                <th>{copy.table.goal}</th>
                <th>{copy.table.format}</th>
                <th>{copy.table.cta}</th>
                <th>{copy.table.source}</th>
                <th>{copy.table.status}</th>
                {hasActions ? <th>{t("Действия")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const itemSource = sourceDisplay(item.source_idea, locale);
                const state = itemState(item);
                const busy = draftingId === item.id;
                return (
                  <tr key={item.id}>
                    <td>{formatDate(item.publish_date, locale)}</td>
                    <td>{item.channel || copy.unknown}</td>
                    <td>{item.topic || copy.untitled}</td>
                    <td>{item.goal || copy.unknown}</td>
                    <td>
                      {formatContentType(
                        item.content_type,
                        locale,
                        copy.unknown,
                      )}
                    </td>
                    <td>{item.cta || copy.unknown}</td>
                    <td>
                      {itemSource.url ? (
                        <a
                          className="source-label"
                          href={itemSource.url}
                          rel="noreferrer"
                          target="_blank"
                          title={item.source_idea || itemSource.url}
                        >
                          {itemSource.label}
                          <Icon name="external" />
                        </a>
                      ) : (
                        <span
                          className="source-label source-label-static"
                          title={item.source_idea || itemSource.label}
                        >
                          {itemSource.label}
                        </span>
                      )}
                    </td>
                    <td>
                      <Status value={stateBadge[state]}>
                        {stateLabels[state]}
                      </Status>
                    </td>
                    {hasActions ? (
                      <td>
                        <div className="plan-row-actions">
                          {state === "not_created" ? (
                            <button
                              className="button button-primary button-small"
                              disabled={busy || !onCreateDraft}
                              onClick={() => onCreateDraft?.(item.id)}
                              type="button"
                            >
                              {busy ? copy.creating : t("Создать черновик")}
                            </button>
                          ) : null}

                          {state === "draft" ? (
                            <>
                              <button
                                className="button button-secondary button-small"
                                disabled={busy}
                                onClick={() => onOpenDraft?.(item)}
                                type="button"
                              >
                                {t("Открыть черновик")}
                              </button>
                              <button
                                className="button button-primary button-small"
                                disabled={busy}
                                onClick={() => onPublish?.(item)}
                                type="button"
                              >
                                {t("Опубликовать")}
                              </button>
                              <button
                                className="button button-secondary button-small"
                                disabled={busy}
                                onClick={() => onSchedule?.(item)}
                                type="button"
                              >
                                {t("Запланировать")}
                              </button>
                            </>
                          ) : null}

                          {state === "scheduled" || state === "published" ? (
                            <button
                              className="button button-secondary button-small"
                              disabled={busy}
                              onClick={() => onOpenDraft?.(item)}
                              type="button"
                            >
                              {state === "published"
                                ? t("Посмотреть")
                                : t("Открыть")}
                            </button>
                          ) : null}

                          {state === "error" ? (
                            <button
                              className="button button-primary button-small"
                              disabled={busy}
                              onClick={() => onPublish?.(item)}
                              type="button"
                            >
                              {t("Повторить")}
                            </button>
                          ) : null}

                          {onCreateTask ? (
                            <button
                              className="button button-secondary button-small"
                              disabled={taskingId === item.id}
                              onClick={() => onCreateTask(item)}
                              type="button"
                              title={t("Создать задачу")}
                            >
                              <Icon
                                name={taskingId === item.id ? "sync" : "plus"}
                              />
                              {t("Создать задачу")}
                            </button>
                          ) : null}
                        </div>
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <span className="empty-icon">
            <Icon name="book" />
          </span>
          <h2>{copy.emptyTitle}</h2>
          <p>{copy.emptyText}</p>
          <div className="empty-actions">
            <Link className="button button-primary" href="#new-plan">
              {copy.manualCreate}
            </Link>
            <Link className="button button-secondary" href="/market-scan">
              {copy.runMarketScan}
              <Icon name="arrow" />
            </Link>
            <Link className="button button-secondary" href="/reports">
              {copy.openReports}
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
