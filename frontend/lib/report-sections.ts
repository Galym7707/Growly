import { asStrings } from "./report-data";

export type ReportSection = {
  key: string;
  title: string;
  items: string[];
};

/**
 * Ordered report sections. Each definition lists the structured-payload keys
 * that may carry the data, trying market-scan keys and competitor-report
 * synonyms in turn so a single component renders both report types.
 */
const SECTION_DEFS: { key: string; title: string; sources: string[] }[] = [
  { key: "audience_pains", title: "Боли клиентов", sources: ["audience_pains"] },
  {
    key: "repeated_offers",
    title: "Повторяющиеся офферы",
    sources: ["repeated_offers", "repeating_offers"],
  },
  {
    key: "repeated_ctas",
    title: "Повторяющиеся призывы",
    sources: ["repeated_ctas", "repeating_ctas"],
  },
  { key: "content_gaps", title: "Контентные пробелы", sources: ["content_gaps"] },
  { key: "content_ideas", title: "Идеи контента", sources: ["content_ideas"] },
  { key: "dominant_topics", title: "Доминирующие темы", sources: ["dominant_topics"] },
  {
    key: "opportunities",
    title: "Возможности",
    sources: ["recommended_positioning", "opportunities"],
  },
  { key: "objections", title: "Возражения", sources: ["objections"] },
  {
    key: "weekly",
    title: "Что сделать на этой неделе",
    sources: ["weekly_priorities", "actions_this_week"],
  },
  {
    key: "risks",
    title: "Риски и ограничения",
    sources: ["risks_and_limitations", "limitations", "risks"],
  },
];

export function reportSections(
  structure: Record<string, unknown> | null | undefined,
): ReportSection[] {
  const source = structure || {};
  const sections: ReportSection[] = [];
  for (const def of SECTION_DEFS) {
    let items: string[] = [];
    for (const key of def.sources) {
      const values = asStrings(source[key]);
      if (values.length) {
        items = values;
        break;
      }
    }
    if (items.length) {
      sections.push({ key: def.key, title: def.title, items });
    }
  }
  return sections;
}

/**
 * Trim a verbose conclusion to the first few sentences so the highlighted
 * "Главный вывод" card stays short while the full detail lives in sections
 * below.
 */
export function shortConclusion(
  text: string | null | undefined,
  maxSentences = 5,
): string {
  const clean = (text || "").replace(/\s+/g, " ").trim();
  if (!clean) return "";
  const sentences = clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [clean];
  return sentences
    .slice(0, Math.max(1, maxSentences))
    .join(" ")
    .trim();
}
