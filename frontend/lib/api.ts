import { localeTag, type Locale } from "./i18n";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/growly${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = (await response.json().catch(() => ({}))) as {
    detail?: string;
  };
  if (!response.ok) {
    throw new ApiError(
      body.detail || "Сервис временно недоступен.",
      response.status,
    );
  }
  return body as T;
}

export function formatDate(
  value: string | null | undefined,
  locale: Locale = "ru",
): string {
  if (!value)
    return locale === "en" ? "No data" : locale === "kk" ? "Дерек жоқ" : "Нет данных";
  return new Intl.DateTimeFormat(localeTag(locale), {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatDateTime(
  value: string | null | undefined,
  locale: Locale = "ru",
): string {
  if (!value)
    return locale === "en"
      ? "Not synced"
      : locale === "kk"
        ? "Синхрондалмаған"
        : "Не синхронизировалось";
  return new Intl.DateTimeFormat(localeTag(locale), {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatReportType(
  value: string | null | undefined,
  locale: Locale = "ru",
): string {
  const labels: Record<string, string> = {
    competitor: "Конкурентный отчёт",
    competitor_report: "Конкурентный отчёт",
    content_plan_source_summary: "Сводка источников",
    market_scan: "Анализ рынка",
    performance: "Результаты публикаций",
    source_monitoring: "Мониторинг источников",
  };
  const label = labels[value || ""] || "Отчёт";
  const translated: Record<Locale, Record<string, string>> = {
    ru: {},
    en: {
      "Конкурентный отчёт": "Competitor report",
      "Сводка источников": "Source summary",
      "Анализ рынка": "Market analysis",
      "Результаты публикаций": "Publication performance",
      "Мониторинг источников": "Source monitoring",
      "Отчёт": "Report",
    },
    kk: {
      "Конкурентный отчёт": "Бәсекелестер есебі",
      "Сводка источников": "Дереккөздер жиынтығы",
      "Анализ рынка": "Нарықты талдау",
      "Результаты публикаций": "Жарияланым нәтижелері",
      "Мониторинг источников": "Дереккөздерді бақылау",
      "Отчёт": "Есеп",
    },
  };
  return translated[locale][label] || label;
}

export function formatReportTitle(
  title: string | null | undefined,
  type: string | null | undefined,
  locale: Locale = "ru",
): string {
  const value = (title || "").trim();
  const normalized = value.toLowerCase();
  if (normalized.startsWith("competitor report")) {
    const suffix = value.split(":").slice(1).join(":").trim();
    return suffix && suffix.toLowerCase() !== "latest evidence"
      ? `${formatReportType("competitor", locale)}: ${suffix}`
      : formatReportType("competitor", locale);
  }
  if (normalized.startsWith("market scan")) {
    const suffix = value.split(":").slice(1).join(":").trim();
    return suffix
      ? `${formatReportType("market_scan", locale)}: ${suffix}`
      : formatReportType("market_scan", locale);
  }
  return value || formatReportType(type, locale);
}
