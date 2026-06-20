import type { ContentPlanOptions } from "./types";

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
  "Спросите по выбранному отчёту или выберите действие";
export const CHAT_PLACEHOLDER_NO_CONTEXT =
  "Сначала выберите отчёт или опишите нишу, продукт и регион";

export const ACTIVE_REPORT_STORAGE_KEY = "growly_active_report_id";

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
  const body: ContentPlanRequestBody = {
    weekly_objective: weeklyObjective,
    business: { language: locale },
    language: locale,
  };
  if (hasActiveContext(active)) {
    (body as Record<string, unknown>).report_id = active!.report_id;
  }
  return body;
}

export type ContentPlanSelections = {
  goal: string;
  audience: string;
  offer: string;
  channels: string[];
  contentTypes: string[];
  cta: string;
  customInstruction: string;
};

export type ContentPlanSubmitBody = {
  report_id: number | null;
  goal: string;
  audience: string;
  offer: string;
  channels: string[];
  content_types: string[];
  cta: string;
  custom_instruction: string;
  language: string;
};

/**
 * Build the guided content-plan submit payload from chip selections. Always
 * carries the report_id so the backend generates the plan from that report.
 */
export function contentPlanSubmitBody(
  reportId: number | null,
  selections: ContentPlanSelections,
  locale: string,
): ContentPlanSubmitBody {
  return {
    report_id: reportId,
    goal: selections.goal.trim(),
    audience: selections.audience.trim(),
    offer: selections.offer.trim(),
    channels: selections.channels,
    content_types: selections.contentTypes,
    cta: selections.cta.trim(),
    custom_instruction: selections.customInstruction.trim(),
    language: locale,
  };
}

/**
 * Which view the content-plan page renders. A single source of truth so the
 * picker and the form are never shown at the same time (and never both hidden).
 */
export function contentPlanMode(
  active: ActiveContext | null,
  manual: boolean,
): "form" | "manual" | "picker" {
  if (hasActiveContext(active) && !manual) return "form";
  if (manual) return "manual";
  return "picker";
}

export function chatMode(
  active: ActiveContext | null,
  skipReport: boolean,
): "workspace" | "picker" {
  return hasActiveContext(active) || skipReport ? "workspace" : "picker";
}

export type ChatRequestBody = {
  action: string | null;
  message: string;
  context: Record<string, unknown>;
  report_id: number | null;
  language: string;
};

/** Every chat request carries the selected report id when one is active. */
export function chatRequestBody(
  active: ActiveContext | null,
  action: string | null,
  message: string,
  context: Record<string, unknown>,
  locale: string,
): ChatRequestBody {
  return {
    action,
    message,
    context,
    report_id: hasActiveContext(active) ? active!.report_id : null,
    language: locale,
  };
}

type FallbackLang = "ru" | "en" | "kk";
const FALLBACK_LANGS: FallbackLang[] = ["ru", "en", "kk"];
const FALLBACK_NICHE = { ru: "ниши", en: "the niche", kk: "нишаның" };
const FALLBACK_GOALS = {
  ru: [
    "Получить больше заявок",
    "Повысить доверие к сервису",
    "Продать ключевую услугу",
    "Объяснить ценность предложения",
  ],
  en: [
    "Get more leads",
    "Build service trust",
    "Sell the core service",
    "Explain the value proposition",
  ],
  kk: [
    "Көбірек өтінім алу",
    "Қызметке сенімді арттыру",
    "Негізгі қызметті сату",
    "Ұсыныс құндылығын түсіндіру",
  ],
};
const FALLBACK_AUDIENCES = {
  ru: [
    "Клиенты ниши «{topic}»",
    "Малый и средний бизнес",
    "Новые потенциальные клиенты",
    "Текущие клиенты для повторных продаж",
  ],
  en: [
    "Customers in the «{topic}» niche",
    "Small and medium business",
    "New potential clients",
    "Existing clients for repeat sales",
  ],
  kk: [
    "«{topic}» нишасының клиенттері",
    "Шағын және орта бизнес",
    "Жаңа әлеуетті клиенттер",
    "Қайта сатуға арналған тұрақты клиенттер",
  ],
};
const FALLBACK_OFFERS = {
  ru: [
    "Основная услуга для ниши «{topic}»",
    "Пробное предложение со скидкой",
    "Комплексный пакет услуг",
    "Консультация по теме «{topic}»",
  ],
  en: [
    "Core service for the «{topic}» niche",
    "Discounted trial offer",
    "Bundled service package",
    "Consultation about «{topic}»",
  ],
  kk: [
    "«{topic}» нишасына негізгі қызмет",
    "Жеңілдікпен сынақ ұсынысы",
    "Кешенді қызмет пакеті",
    "«{topic}» бойынша кеңес",
  ],
};
const FALLBACK_CONTENT_TYPES = {
  ru: ["Пост", "Reels / короткое видео", "Stories", "Кейс клиента", "FAQ / ответы на вопросы"],
  en: ["Post", "Reels / short video", "Stories", "Customer case", "FAQ"],
  kk: ["Пост", "Reels / қысқа видео", "Stories", "Клиент кейсі", "Жиі қойылатын сұрақтар"],
};
const FALLBACK_CTAS = {
  ru: ["Оставить заявку", "Получить консультацию", "Узнать стоимость", "Написать в Telegram"],
  en: ["Leave a request", "Get a consultation", "Find out the price", "Message us on Telegram"],
  kk: ["Өтінім қалдыру", "Кеңес алу", "Бағасын білу", "Telegram-ға жазу"],
};

/**
 * Report-derived default options used when the backend option endpoint is
 * unavailable, so the guided form is always usable. Topic-anchored — never
 * unrelated hardcoded niches.
 */
export function fallbackContentPlanOptions(
  active: ActiveContext | null,
  locale: string,
): ContentPlanOptions {
  const lang: FallbackLang = FALLBACK_LANGS.includes(locale as FallbackLang)
    ? (locale as FallbackLang)
    : "ru";
  const topic = activeContextTopic(active) || FALLBACK_NICHE[lang];
  const tmpl = (items: string[]) =>
    items.map((item) => {
      const value = item.replace("{topic}", topic);
      return { label: value.slice(0, 60), value };
    });
  return {
    goals: tmpl(FALLBACK_GOALS[lang]),
    audiences: tmpl(FALLBACK_AUDIENCES[lang]),
    offers: tmpl(FALLBACK_OFFERS[lang]),
    channels: [
      { label: "Instagram", value: "instagram" },
      { label: "Telegram", value: "telegram" },
      { label: "WhatsApp", value: "whatsapp" },
    ],
    content_types: tmpl(FALLBACK_CONTENT_TYPES[lang]),
    ctas: tmpl(FALLBACK_CTAS[lang]),
  };
}

type ReportLike = {
  id?: number | string;
  report_id?: number | string;
  title?: string | null;
  type?: string | null;
  report_type?: string | null;
  summary?: string | null;
  query?: string | null;
  sources_count?: number | string | null;
  created_at?: string | null;
  status?: string | null;
  notion_synced?: boolean;
  notion_url?: string | null;
  structure?: Record<string, unknown> | null;
};

/**
 * Build an ActiveContext from a /reports payload so the URL ?reportId param
 * and localStorage can hydrate context without a separate context fetch.
 */
export function buildActiveContextFromReport(
  report: ReportLike | null | undefined,
): ActiveContext | null {
  if (!report) return null;
  const rawId = report.id ?? report.report_id;
  const reportId =
    typeof rawId === "number" && Number.isFinite(rawId)
      ? Math.trunc(rawId)
      : typeof rawId === "string" && /^\d+$/.test(rawId.trim())
        ? Number(rawId.trim())
        : null;
  if (reportId === null) return null;
  const structure =
    report.structure && typeof report.structure === "object"
      ? report.structure
      : {};
  const market =
    structure.market_context && typeof structure.market_context === "object"
      ? (structure.market_context as Record<string, unknown>)
      : {};
  const topic =
    asString(market.topic) || asString(report.query) || asString(report.title);
  return {
    report_id: reportId,
    report_title: asString(report.title),
    report_type: asString(report.report_type) || asString(report.type),
    topic,
    region: asString(market.region),
    language: asString(market.language),
    sources_count: asCount(report.sources_count),
    created_at: asString(report.created_at),
    status: asString(report.status),
    notion_synced: Boolean(report.notion_synced),
    notion_url: asString(report.notion_url),
  };
}
