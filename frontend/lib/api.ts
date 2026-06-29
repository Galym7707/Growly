import { localeTag, type Locale } from "./i18n";

export type ApiDebugInfo = {
  message: string;
  status: number;
  url: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public url: string,
    public responseMessage: string,
  ) {
    super(message);
  }
}

export function buildApiUrl(
  path: string,
): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const proxyPath = normalizedPath.startsWith("/api/")
    ? normalizedPath.slice(4)
    : normalizedPath;
  return `/api/growly${proxyPath}`;
}

export function apiErrorDebugInfo(value: unknown): ApiDebugInfo | null {
  if (!(value instanceof ApiError)) return null;
  return {
    message: value.responseMessage,
    status: value.status,
    url: value.url,
  };
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const requestedUrl = buildApiUrl(path);
  let response: Response;
  try {
    response = await fetch(requestedUrl, {
      ...options,
      credentials: options.credentials ?? "include",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (value) {
    const responseMessage =
      value instanceof Error ? value.message : "Network request failed";
    const error = new ApiError(
      "Сервис временно недоступен.",
      0,
      sanitizeApiUrl(requestedUrl),
      responseMessage,
    );
    logApiFailure(error);
    throw error;
  }
  const responseText = await response.text();
  const body = parseResponseBody(responseText);
  const responseMessage = extractResponseMessage(
    body,
    responseText,
    response.statusText,
  );
  if (!response.ok) {
    const error = new ApiError(
      responseMessage || "Сервис временно недоступен.",
      response.status,
      sanitizeApiUrl(requestedUrl),
      responseMessage || response.statusText,
    );
    logApiFailure(error);
    throw error;
  }
  return body as T;
}

export function sanitizeApiUrl(value: string): string {
  try {
    const url = new URL(value, "http://growly.local");
    for (const key of Array.from(url.searchParams.keys())) {
      if (/(key|token|secret|password|auth|session)/i.test(key)) {
        url.searchParams.set(key, "[redacted]");
      }
    }
    if (value.startsWith("/")) {
      return `${url.pathname}${url.search}`;
    }
    return url.toString();
  } catch {
    return value.replace(
      /([?&][^=]*(?:key|token|secret|password|auth|session)[^=]*=)[^&]+/gi,
      "$1[redacted]",
    );
  }
}

function parseResponseBody(value: string): Record<string, unknown> {
  if (!value.trim()) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" ? parsed : { detail: value };
  } catch {
    return { detail: value.trim() };
  }
}

function extractResponseMessage(
  body: Record<string, unknown>,
  responseText: string,
  statusText: string,
): string {
  const detail = body.detail;
  const message = body.message;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (typeof message === "string" && message.trim()) return message.trim();
  return responseText.trim() || statusText || "Сервис временно недоступен.";
}

function logApiFailure(error: ApiError): void {
  if (process.env.NODE_ENV !== "development") return;
  console.debug("[Growly API]", {
    message: error.responseMessage,
    status: error.status,
    url: error.url,
  });
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

export function formatStatusLabel(
  value: string | null | undefined,
  locale: Locale = "ru",
): string {
  const normalized = (value || "").toLowerCase().trim();
  const labels: Record<Locale, Record<string, string>> = {
    ru: {
      active: "Активен",
      approved: "Согласован",
      canceled: "Отменён",
      cancelled: "Отменён",
      completed: "Завершён",
      disabled: "Отключён",
      done: "Готово",
      failed: "Ошибка",
      free: "Бесплатный",
      in_progress: "В работе",
      pending: "На согласовании",
      pending_approval: "На согласовании",
      published: "Опубликован",
      queued: "В очереди",
      ready: "Готов",
      rejected: "Отклонён",
      running: "Выполняется",
      scheduled: "Запланирован",
      submitted: "Отправлен",
      trialing: "Пробный период",
    },
    en: {
      active: "Active",
      approved: "Approved",
      canceled: "Canceled",
      cancelled: "Canceled",
      completed: "Completed",
      disabled: "Disabled",
      done: "Done",
      failed: "Error",
      free: "Free",
      in_progress: "In progress",
      pending: "Pending approval",
      pending_approval: "Pending approval",
      published: "Published",
      queued: "Queued",
      ready: "Ready",
      rejected: "Rejected",
      running: "Running",
      scheduled: "Scheduled",
      submitted: "Submitted",
      trialing: "Trialing",
    },
    kk: {
      active: "Белсенді",
      approved: "Бекітілді",
      canceled: "Бас тартылды",
      cancelled: "Бас тартылды",
      completed: "Аяқталды",
      disabled: "Өшірілген",
      done: "Дайын",
      failed: "Қате",
      free: "Тегін",
      in_progress: "Жұмыста",
      pending: "Бекітуде",
      pending_approval: "Бекітуде",
      published: "Жарияланған",
      queued: "Кезекте",
      ready: "Дайын",
      rejected: "Қабылданбады",
      running: "Орындалуда",
      scheduled: "Жоспарланған",
      submitted: "Жіберілді",
      trialing: "Сынақ кезеңі",
    },
  };
  if (!normalized) return locale === "en" ? "No status" : locale === "kk" ? "Күйі жоқ" : "Нет статуса";
  return labels[locale][normalized] || value || normalized;
}
