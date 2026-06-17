"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { Status } from "@/components/ui";
import { formatDate } from "@/lib/api";
import {
  contentPlanSourceText,
  formatContentStatus,
  formatContentType,
  sourceDisplay,
} from "@/lib/content-plan";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanItem, ContentPlanSource } from "@/lib/types";

type Props = {
  draftingId?: number | null;
  items: ContentPlanItem[];
  onCreateDraft?: (itemId: number) => void;
  source?: ContentPlanSource | null;
};

export function ContentPlanView({
  draftingId = null,
  items,
  onCreateDraft,
  source = null,
}: Props) {
  const { locale } = useLanguage();
  const copy = contentPlanCopy(locale);

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
                {onCreateDraft ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const source = sourceDisplay(item.source_idea, locale);
                const statusLabel = formatContentStatus(item.status, locale);
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
                      {source.url ? (
                        <a
                          className="source-label"
                          href={source.url}
                          rel="noreferrer"
                          target="_blank"
                          title={item.source_idea || source.url}
                        >
                          {source.label}
                          <Icon name="external" />
                        </a>
                      ) : (
                        <span
                          className="source-label source-label-static"
                          title={item.source_idea || source.label}
                        >
                          {source.label}
                        </span>
                      )}
                    </td>
                    <td>
                      <Status value={item.status}>
                        {statusLabel || item.status}
                      </Status>
                    </td>
                    {onCreateDraft ? (
                      <td>
                        <button
                          className="button button-secondary button-small"
                          disabled={
                            draftingId === item.id || item.status === "drafted"
                          }
                          onClick={() => onCreateDraft(item.id)}
                          type="button"
                        >
                          {draftingId === item.id
                            ? copy.creating
                            : item.status === "drafted"
                              ? copy.created
                              : copy.createDraft}
                        </button>
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
