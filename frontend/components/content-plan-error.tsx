"use client";

import Link from "next/link";
import type { ApiDebugInfo } from "@/lib/api";
import { contentPlanCopy } from "@/lib/content-plan-copy";
import { useLanguage } from "@/lib/i18n";

type Props = {
  debugInfo?: ApiDebugInfo | null;
  manualHref?: string;
  onRetry: () => void;
};

export function ContentPlanErrorPanel({
  debugInfo = null,
  manualHref = "#new-plan",
  onRetry,
}: Props) {
  const { locale } = useLanguage();
  const copy = contentPlanCopy(locale);
  const showDebug = process.env.NODE_ENV === "development" && debugInfo;

  return (
    <section className="content-plan-error" role="alert">
      <div>
        <h2>{copy.loadErrorTitle}</h2>
        <p className="content-plan-error-label">
          {copy.loadErrorReasonsTitle}
        </p>
        <ul>
          {copy.loadErrorReasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>
      <div className="feedback-actions">
        <button
          className="button button-secondary button-small"
          onClick={onRetry}
          type="button"
        >
          {copy.retry}
        </button>
        <Link className="button button-secondary button-small" href="/reports">
          {copy.openReports}
        </Link>
        <Link className="button button-secondary button-small" href={manualHref}>
          {copy.manualCreate}
        </Link>
      </div>
      {showDebug ? (
        <details className="api-debug">
          <summary>{copy.debug.title}</summary>
          <dl>
            <div>
              <dt>{copy.debug.url}</dt>
              <dd>{debugInfo.url}</dd>
            </div>
            <div>
              <dt>{copy.debug.status}</dt>
              <dd>{debugInfo.status}</dd>
            </div>
            <div>
              <dt>{copy.debug.message}</dt>
              <dd>{debugInfo.message}</dd>
            </div>
          </dl>
        </details>
      ) : null}
    </section>
  );
}
