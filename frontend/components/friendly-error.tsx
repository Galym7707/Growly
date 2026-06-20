"use client";

import type { ApiDebugInfo } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

const DEFAULT_MESSAGE =
  "Не удалось загрузить данные. Попробуйте ещё раз или выберите другой отчёт.";

type Props = {
  debug?: ApiDebugInfo | null;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
};

/**
 * User-facing error: a friendly localized message with technical details
 * hidden behind a collapsible block in development only. Never exposes tokens
 * or secrets — debug URLs are already sanitized by the API client.
 */
export function FriendlyError({
  debug = null,
  message,
  onRetry,
  retryLabel,
}: Props) {
  const { t } = useLanguage();
  const showDebug = process.env.NODE_ENV === "development" && debug;

  return (
    <div className="feedback feedback-error" role="alert">
      <p>{message ? message : t(DEFAULT_MESSAGE)}</p>
      {onRetry ? (
        <div className="feedback-actions">
          <button
            className="button button-secondary button-small"
            onClick={onRetry}
            type="button"
          >
            {retryLabel ? retryLabel : t("Повторить")}
          </button>
        </div>
      ) : null}
      {showDebug ? (
        <details className="api-debug">
          <summary>{t("Технические детали")}</summary>
          <dl>
            <div>
              <dt>Requested URL</dt>
              <dd>{debug.url}</dd>
            </div>
            <div>
              <dt>Status code</dt>
              <dd>{debug.status}</dd>
            </div>
            <div>
              <dt>Response message</dt>
              <dd>{debug.message}</dd>
            </div>
          </dl>
        </details>
      ) : null}
    </div>
  );
}
