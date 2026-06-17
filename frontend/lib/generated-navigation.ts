type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}

function normalizeId(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  return null;
}

function firstId(...values: unknown[]): string | null {
  for (const value of values) {
    const id = normalizeId(value);
    if (id) return id;
  }
  return null;
}

export function extractGeneratedReportId(value: unknown): string | null {
  const response = asRecord(value);
  if (!response) return null;
  const report = asRecord(response.report);
  return firstId(
    response.report_id,
    response.id,
    response.reportId,
    report?.id,
  );
}

export function reportPathFromGeneratedResponse(value: unknown): string | null {
  const reportId = extractGeneratedReportId(value);
  return reportId ? `/reports/${encodeURIComponent(reportId)}` : null;
}

export function extractGeneratedDraftId(value: unknown): string | null {
  const response = asRecord(value);
  if (!response) return null;
  const draft = asRecord(response.draft);
  return firstId(response.draft_id, response.id, response.draftId, draft?.id);
}

export function extractGeneratedContentPlanId(value: unknown): string | null {
  const response = asRecord(value);
  if (!response) return null;
  const item = asRecord(response.item);
  const firstItem =
    Array.isArray(response.items) && response.items.length
      ? asRecord(response.items[0])
      : null;
  return firstId(
    response.plan_id,
    response.content_plan_id,
    response.id,
    response.contentPlanId,
    item?.id,
    firstItem?.id,
  );
}

export function contentPlanPathFromGeneratedResponse(
  value: unknown,
): string | null {
  const contentPlanId = extractGeneratedContentPlanId(value);
  return contentPlanId
    ? `/content-plan/${encodeURIComponent(contentPlanId)}`
    : null;
}
