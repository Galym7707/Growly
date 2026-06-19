import { describe, expect, it } from "vitest";
import {
  isFailedMarketScanJob,
  marketScanErrorMessage,
  marketScanJobPath,
  marketScanStepIndex,
} from "../lib/market-scan-job";

describe("market scan background job", () => {
  it("builds a safe polling path", () => {
    expect(marketScanJobPath("job/123")).toBe(
      "/market-scan/jobs/job%2F123",
    );
  });

  it("maps backend progress to the visible five steps", () => {
    expect(marketScanStepIndex("Шаг 1/5: ищу источники")).toBe(0);
    expect(marketScanStepIndex("Шаг 4/5: анализирую")).toBe(3);
    expect(marketScanStepIndex("Шаг 5/5: сохраняю отчёт")).toBe(4);
    expect(marketScanStepIndex("Готово.")).toBe(0);
  });

  it("recognizes terminal failure states", () => {
    expect(isFailedMarketScanJob("failed")).toBe(true);
    expect(isFailedMarketScanJob("cancelled")).toBe(true);
    expect(isFailedMarketScanJob("running")).toBe(false);
  });

  it("replaces raw Vercel timeout output with a user-facing message", () => {
    expect(
      marketScanErrorMessage(
        "An error occurred with your deployment FUNCTION_INVOCATION_TIMEOUT fra1",
      ),
    ).toBe("Сервер не успел запустить анализ. Повторите попытку.");
  });
});
