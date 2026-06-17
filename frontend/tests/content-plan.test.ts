import { describe, expect, it } from "vitest";
import {
  formatContentStatus,
  formatContentType,
  sourceDisplay,
} from "../lib/content-plan";
import { contentPlanCopy } from "../lib/content-plan-copy";

describe("content plan presentation", () => {
  it("localizes backend enum values", () => {
    expect(formatContentType("weekly_digest", "ru", "Не указан")).toBe(
      "Еженедельный обзор",
    );
    expect(formatContentType("message", "en", "Not specified")).toBe(
      "Message",
    );
    expect(formatContentStatus("published", "kk")).toBe("Жарияланды");
  });

  it("does not expose raw source URLs as table labels", () => {
    const source = sourceDisplay(
      "https://instagram.com/reel/example supporting evidence",
      "ru",
    );

    expect(source.url).toBe("https://instagram.com/reel/example");
    expect(source.label).toBe("Instagram Reel");
    expect(source.label).not.toContain("https://");
  });

  it("uses friendly Russian empty and load error copy", () => {
    const copy = contentPlanCopy("ru");

    expect(copy.emptyText).toBe(
      "Пока нет контент-плана. Создайте план на основе последнего анализа рынка.",
    );
    expect(copy.loadErrorTitle).toBe("Не удалось загрузить контент-план.");
    expect(copy.loadErrorReasons).toEqual([
      "контент-план ещё не создан",
      "сервер временно недоступен",
      "endpoint backend не найден",
    ]);
  });
});
