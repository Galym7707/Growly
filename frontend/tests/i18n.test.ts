import { describe, expect, it } from "vitest";
import { localeTag, translate } from "../lib/i18n";

describe("Growly i18n", () => {
  it("translates core navigation to English and Kazakh", () => {
    expect(translate("en", "Анализ рынка")).toBe("Market analysis");
    expect(translate("kk", "Анализ рынка")).toBe("Нарықты талдау");
  });

  it("interpolates translated values", () => {
    expect(translate("en", "Всего: {count}", { count: 4 })).toBe("Total: 4");
    expect(translate("kk", "Всего: {count}", { count: 4 })).toBe("Барлығы: 4");
  });

  it("uses locale-specific Intl tags", () => {
    expect(localeTag("ru")).toBe("ru-RU");
    expect(localeTag("en")).toBe("en-US");
    expect(localeTag("kk")).toBe("kk-KZ");
  });
});
