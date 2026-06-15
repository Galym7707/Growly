export type CompetitorRow = {
  competitor?: string;
  channel?: string;
  offer?: string;
  price_value?: string;
  cta?: string;
  strengths?: string;
  weaknesses?: string;
  opportunity?: string;
};

export function asStrings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map(String).filter((item) => item.trim())
    : [];
}

export function asCompetitors(value: unknown): CompetitorRow[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is CompetitorRow =>
          Boolean(item) && typeof item === "object",
      )
    : [];
}

export function asMetricRows(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          Boolean(item) && typeof item === "object",
      )
    : [];
}
