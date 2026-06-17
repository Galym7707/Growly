import type { Locale } from "./i18n";
import type { ContentPlanItem, ContentPlanSource } from "./types";

type SourceDisplay = {
  label: string;
  url: string | null;
};

const contentTypeLabels: Record<string, Record<Locale, string>> = {
  post: { ru: "Пост", en: "Post", kk: "Пост" },
  reels: { ru: "Reels", en: "Reels", kk: "Reels" },
  reel: { ru: "Reels", en: "Reels", kk: "Reels" },
  story: { ru: "Stories", en: "Stories", kk: "Stories" },
  stories: { ru: "Stories", en: "Stories", kk: "Stories" },
  weekly_digest: {
    ru: "Еженедельный обзор",
    en: "Weekly digest",
    kk: "Апталық шолу",
  },
  "weekly digest": {
    ru: "Еженедельный обзор",
    en: "Weekly digest",
    kk: "Апталық шолу",
  },
  message: { ru: "Сообщение", en: "Message", kk: "Хабарлама" },
};

const statusLabels: Record<string, Record<Locale, string>> = {
  draft: { ru: "Черновик", en: "Draft", kk: "Черновик" },
  approved: { ru: "Одобрено", en: "Approved", kk: "Мақұлданды" },
  published: { ru: "Опубликовано", en: "Published", kk: "Жарияланды" },
  failed: { ru: "Ошибка", en: "Failed", kk: "Қате" },
};

export function formatContentType(
  value: string | null | undefined,
  locale: Locale,
  fallback: string,
): string {
  const normalized = (value || "").trim().toLowerCase().replaceAll("-", "_");
  return contentTypeLabels[normalized]?.[locale] || value || fallback;
}

export function formatContentStatus(
  value: string | null | undefined,
  locale: Locale,
): string {
  const normalized = (value || "").trim().toLowerCase();
  return statusLabels[normalized]?.[locale] || value || "";
}

export function contentPlanPathFromResponse(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const response = value as Record<string, unknown>;
  const id = response.plan_id ?? response.content_plan_id ?? response.id;
  if (typeof id === "number" && Number.isFinite(id)) {
    return `/content-plan/${id}`;
  }
  if (typeof id === "string" && id.trim()) {
    return `/content-plan/${encodeURIComponent(id.trim())}`;
  }
  return null;
}

export function sourceDisplay(
  value: string | null | undefined,
  locale: Locale,
): SourceDisplay {
  const text = (value || "").trim();
  const url = extractUrl(text);
  const haystack = `${text} ${url || ""}`.toLowerCase();
  if (haystack.includes("instagram")) {
    return { label: "Instagram Reel", url };
  }
  if (haystack.includes("telegram") || haystack.includes("t.me")) {
    return { label: locale === "en" ? "Telegram post" : "Telegram-пост", url };
  }
  const reportId = text.match(/(?:report|отч[её]т|анализ|market scan)\D+#?(\d+)/i);
  if (reportId) {
    const prefix = locale === "en" ? "Market scan" : "Анализ рынка";
    return { label: `${prefix} #${reportId[1]}`, url };
  }
  if (url) {
    const host = hostLabel(url);
    const label =
      host && !host.includes("example")
        ? host
        : locale === "en"
          ? "Competitor website"
          : locale === "kk"
            ? "Бәсекелес сайты"
            : "Сайт конкурента";
    return { label, url };
  }
  if (!text || /limited|internal|внутрен|огранич/i.test(text)) {
    return {
      label:
        locale === "en"
          ? "Internal data"
          : locale === "kk"
            ? "Ішкі деректер"
            : "Внутренние данные",
      url: null,
    };
  }
  return {
    label:
      locale === "en"
        ? "Market insight"
        : locale === "kk"
          ? "Нарық талдауы"
          : "Анализ рынка",
    url: null,
  };
}

export function contentPlanSourceText(
  source: ContentPlanSource | null | undefined,
  locale: Locale,
): string {
  if (!source) {
    return locale === "en"
      ? "Based on: no market scan linked yet."
      : locale === "kk"
        ? "Негізі: нарық талдауы әлі байланыстырылмаған."
        : "Основа: анализ рынка ещё не привязан.";
  }
  const language = source.language || locale;
  const synced = source.notion_synced
    ? locale === "en"
      ? "synced"
      : locale === "kk"
        ? "сақталған"
        : "сохранено"
    : locale === "en"
      ? "not synced"
      : locale === "kk"
        ? "сақталмаған"
        : "не сохранено";
  if (locale === "en") {
    return `Based on: ${source.report_title || "latest market scan"}. Report ID: ${source.report_id}. Sources: ${source.sources_count}. Language: ${language}. Notion: ${synced}.`;
  }
  if (locale === "kk") {
    return `Негізі: ${source.report_title || "соңғы нарық талдауы"}. Есеп ID: ${source.report_id}. Дереккөздер: ${source.sources_count}. Тіл: ${language}. Notion: ${synced}.`;
  }
  return `План создан на основе анализа рынка: ${source.report_title || "последний отчёт"}. Отчёт ID: ${source.report_id}. Источников: ${source.sources_count}. Язык: ${language}. Статус Notion: ${synced}.`;
}

export function hasRealContentPlanItems(items: ContentPlanItem[]): boolean {
  return items.length > 0;
}

function extractUrl(value: string): string | null {
  return value.match(/https?:\/\/[^\s)"']+/i)?.[0] || null;
}

function hostLabel(value: string): string | null {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
