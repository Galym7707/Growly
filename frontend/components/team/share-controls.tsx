"use client";

import { useState } from "react";
import { Icon } from "@/components/icons";
import { InviteModal } from "@/components/team/invite-modal";
import { apiRequest } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { useWorkspace } from "@/lib/workspace";

/** "Поделиться с командой" — opens the invite-by-email modal. Owner/admin only. */
export function ShareWithTeamButton({
  className = "button button-secondary",
}: {
  className?: string;
}) {
  const { t } = useLanguage();
  const { workspace } = useWorkspace();
  const [open, setOpen] = useState(false);
  if (!workspace?.permissions.can_manage_team) return null;
  return (
    <>
      <button className={className} onClick={() => setOpen(true)} type="button">
        <Icon name="users" />
        {t("Поделиться с командой")}
      </button>
      {open ? (
        <InviteModal
          workspaceId={workspace.workspace_id}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}

type ShareResource = "report" | "content_plan" | "draft";

/** Creates an unguessable view-only link and copies it. Owner/admin only. */
export function CopyShareLinkButton({
  resourceType,
  resourceId,
  className = "button button-secondary",
}: {
  resourceType: ShareResource;
  resourceId: number;
  className?: string;
}) {
  const { t } = useLanguage();
  const { workspace } = useWorkspace();
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  if (!workspace?.permissions.can_manage_team) return null;

  async function createAndCopy() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await apiRequest<{ share_link: { share_path: string } }>(
        "/share-links",
        {
          method: "POST",
          body: JSON.stringify({
            resource_type: resourceType,
            resource_id: resourceId,
          }),
        },
      );
      const url = `${window.location.origin}${response.share_link.share_path}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        className={className}
        disabled={busy}
        onClick={createAndCopy}
        type="button"
        title={t("Скопировать ссылку для просмотра")}
      >
        <Icon name={busy ? "sync" : copied ? "check" : "external"} />
        {copied ? t("Скопировано") : t("Скопировать ссылку для просмотра")}
      </button>
      {error ? <span className="form-error">{error}</span> : null}
    </>
  );
}
