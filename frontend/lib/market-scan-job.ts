export type MarketScanJobResponse = {
  status?: string;
  job_id?: number | string;
  current_step?: string | null;
  sources_count?: number;
  sources_saved?: number;
  report_id?: number | string | null;
  error_message?: string | null;
};

const failedStatuses = new Set(["failed", "cancelled"]);

export function marketScanJobPath(jobId: number | string): string {
  return `/market-scan/jobs/${encodeURIComponent(String(jobId))}`;
}

export function isFailedMarketScanJob(status: string | undefined): boolean {
  return failedStatuses.has(status || "");
}

export function marketScanErrorMessage(message: string): string {
  return /FUNCTION_INVOCATION_TIMEOUT|error occurred with your deployment/i.test(
    message,
  )
    ? "Сервер не успел запустить анализ. Повторите попытку."
    : message;
}

export function marketScanStepIndex(currentStep: string | null | undefined): number {
  const match = currentStep?.match(/(?:Шаг|Step)\s+(\d+)\s*\/\s*5/i);
  if (!match) return 0;
  return Math.max(0, Math.min(4, Number(match[1]) - 1));
}
