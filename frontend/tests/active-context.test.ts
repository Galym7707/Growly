import { describe, expect, it } from "vitest";
import {
  activeContextTopic,
  chatPlaceholderSource,
  contentPlanRequestBody,
  hasActiveContext,
  normalizeActiveContext,
  type ActiveContext,
} from "../lib/active-context";

const sample: ActiveContext = {
  report_id: 23,
  report_title: "Анализ рынка: Логистика",
  report_type: "market_scan",
  topic: "Логистика и доставка товаров",
  region: "Казахстан",
  language: "ru",
  sources_count: 40,
  created_at: "2026-06-19T10:00:00+00:00",
  status: "ready",
  notion_synced: false,
  notion_url: null,
};

describe("active workspace context", () => {
  it("normalizes a backend payload into a typed context", () => {
    const context = normalizeActiveContext({
      active: {
        report_id: 23,
        report_title: "Анализ рынка: Логистика",
        topic: "Логистика и доставка товаров",
        sources_count: 40,
        created_at: "2026-06-19T10:00:00+00:00",
      },
    });
    expect(context?.report_id).toBe(23);
    expect(context?.topic).toBe("Логистика и доставка товаров");
    expect(context?.sources_count).toBe(40);
  });

  it("returns null when no active report exists", () => {
    expect(normalizeActiveContext({ active: null })).toBeNull();
    expect(normalizeActiveContext({})).toBeNull();
    expect(normalizeActiveContext(undefined)).toBeNull();
  });

  it("coerces a string sources_count and report_id", () => {
    const context = normalizeActiveContext({
      active: { report_id: "23", sources_count: "40" },
    });
    expect(context?.report_id).toBe(23);
    expect(context?.sources_count).toBe(40);
  });

  it("does not ask for the niche again when context is active", () => {
    expect(hasActiveContext(sample)).toBe(true);
    expect(
      chatPlaceholderSource(sample, "Опишите нишу, продукт и регион"),
    ).toBe("Спросите по последнему анализу или выберите действие");
  });

  it("falls back to the niche prompt without active context", () => {
    expect(hasActiveContext(null)).toBe(false);
    expect(
      chatPlaceholderSource(null, "Опишите нишу, продукт и регион"),
    ).toBe("Опишите нишу, продукт и регион");
  });

  it("exposes the active topic for context banners", () => {
    expect(activeContextTopic(sample)).toBe("Логистика и доставка товаров");
    expect(activeContextTopic(null)).toBeNull();
  });

  it("pins the content plan to the active report by default", () => {
    const body = contentPlanRequestBody(sample, "Trust", "ru");
    expect(body.business.market_context).toEqual({ report_id: 23 });
    expect(body.weekly_objective).toBe("Trust");
  });

  it("omits the market context when no analysis is active", () => {
    const body = contentPlanRequestBody(null, "Trust", "en");
    expect(body.business).toEqual({ language: "en" });
    expect(body.business.market_context).toBeUndefined();
  });
});
