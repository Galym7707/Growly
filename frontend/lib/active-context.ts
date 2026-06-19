export type ActiveContext = {
  report_id: number;
  report_title: string | null;
  report_type: string | null;
  topic: string | null;
  region: string | null;
  language: string | null;
  sources_count: number;
  created_at: string | null;
  status: string | null;
  notion_synced: boolean;
  notion_url: string | null;
};

export type ActiveContextResponse = { active: ActiveContext | null };

export const CHAT_PLACEHOLDER_WITH_CONTEXT =
  "Спросите по последнему анализу или выберите действие";
export const CHAT_PLACEHOLDER_NO_CONTEXT = "Опишите нишу, продукт и регион";

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  return null;
}

function asCount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, Math.trunc(value));
  }
  if (typeof value === "string" && /^\d+$/.test(value.trim())) {
    return Number(value.trim());
  }
  return 0;
}

export function normalizeActiveContext(value: unknown): ActiveContext | null {
  if (!value || typeof value !== "object") return null;
  const active = (value as { active?: unknown }).active;
  if (!active || typeof active !== "object") return null;
  const record = active as Record<string, unknown>;
  const rawId = record.report_id;
  const reportId =
    typeof rawId === "number" && Number.isFinite(rawId)
      ? Math.trunc(rawId)
      : typeof rawId === "string" && /^\d+$/.test(rawId.trim())
        ? Number(rawId.trim())
        : null;
  if (reportId === null) return null;
  return {
    report_id: reportId,
    report_title: asString(record.report_title),
    report_type: asString(record.report_type),
    topic: asString(record.topic),
    region: asString(record.region),
    language: asString(record.language),
    sources_count: asCount(record.sources_count),
    created_at: asString(record.created_at),
    status: asString(record.status),
    notion_synced: Boolean(record.notion_synced),
    notion_url: asString(record.notion_url),
  };
}

export function hasActiveContext(active: ActiveContext | null): boolean {
  return Boolean(active && active.report_id);
}

export function activeContextTopic(active: ActiveContext | null): string | null {
  if (!active) return null;
  const topic = (active.topic || active.report_title || "").trim();
  return topic || null;
}

/**
 * Chat input placeholder. When a previous analysis is active, prompt the user
 * to ask about it instead of re-describing the niche from scratch.
 */
export function chatPlaceholderSource(
  active: ActiveContext | null,
  fallbackSource: string,
): string {
  return hasActiveContext(active)
    ? CHAT_PLACEHOLDER_WITH_CONTEXT
    : fallbackSource;
}

export type ContentPlanRequestBody = {
  weekly_objective: string;
  business: Record<string, unknown>;
  language: string;
};

/**
 * Build the content-plan generation payload. When an analysis is active the
 * plan is pinned to that report so the user is not asked to re-enter the niche.
 */
export function contentPlanRequestBody(
  active: ActiveContext | null,
  weeklyObjective: string,
  locale: string,
): ContentPlanRequestBody {
  const business: Record<string, unknown> = { language: locale };
  if (hasActiveContext(active)) {
    business.market_context = { report_id: active!.report_id };
  }
  return { weekly_objective: weeklyObjective, business, language: locale };
}
