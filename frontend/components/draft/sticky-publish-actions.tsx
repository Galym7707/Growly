"use client";

import { Icon } from "@/components/icons";
import { useLanguage } from "@/lib/i18n";

export function StickyPublishActions({
  label,
  busyLabel,
  busy,
  disabled,
  reason,
  onPrimary,
}: {
  label: string;
  busyLabel: string;
  busy: boolean;
  disabled: boolean;
  reason: string | null;
  onPrimary: () => void;
}) {
  const { t } = useLanguage();
  return (
    <div className="publish-actions">
      <button
        className="button button-primary button-wide"
        disabled={disabled || busy}
        onClick={onPrimary}
        type="button"
      >
        <Icon name={busy ? "sync" : "arrow"} />
        {busy ? t(busyLabel) : t(label)}
      </button>
      {reason && !busy ? <p className="publish-reason">{t(reason)}</p> : null}
    </div>
  );
}
