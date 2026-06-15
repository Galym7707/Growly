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

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Нет данных";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Не синхронизировалось";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatReportType(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    competitor: "Конкурентный отчёт",
    competitor_report: "Конкурентный отчёт",
    content_plan_source_summary: "Сводка источников",
    market_scan: "Анализ рынка",
    performance: "Результаты публикаций",
    source_monitoring: "Мониторинг источников",
  };
  return labels[value || ""] || "Отчёт";
}

export function formatReportTitle(
  title: string | null | undefined,
  type: string | null | undefined,
): string {
  const value = (title || "").trim();
  const normalized = value.toLowerCase();
  if (normalized.startsWith("competitor report")) {
    const suffix = value.split(":").slice(1).join(":").trim();
    return suffix && suffix.toLowerCase() !== "latest evidence"
      ? `Конкурентный отчёт: ${suffix}`
      : "Конкурентный отчёт";
  }
  if (normalized.startsWith("market scan")) {
    const suffix = value.split(":").slice(1).join(":").trim();
    return suffix ? `Анализ рынка: ${suffix}` : "Анализ рынка";
  }
  return value || formatReportType(type);
}
