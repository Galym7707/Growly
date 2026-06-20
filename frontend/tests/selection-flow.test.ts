import { describe, expect, it } from "vitest";
import {
  chatMode,
  chatRequestBody,
  contentPlanMode,
  fallbackContentPlanOptions,
  type ActiveContext,
} from "../lib/active-context";

const active: ActiveContext = {
  report_id: 23,
  report_title: "Анализ рынка: Логистика и доставка товаров",
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

describe("selection flow", () => {
  it("shows the form when a report is selected and the picker otherwise", () => {
    expect(contentPlanMode(active, false)).toBe("form");
    expect(contentPlanMode(null, false)).toBe("picker");
  });

  it("switches the content plan to manual mode", () => {
    expect(contentPlanMode(null, true)).toBe("manual");
    expect(contentPlanMode(active, true)).toBe("manual");
  });

  it("opens the chat workspace once a report is selected or skipped", () => {
    expect(chatMode(active, false)).toBe("workspace");
    expect(chatMode(null, true)).toBe("workspace");
    expect(chatMode(null, false)).toBe("picker");
  });

  it("includes the selected report id in every chat request", () => {
    const body = chatRequestBody(active, "ask", "Какие боли?", {}, "ru");
    expect(body.report_id).toBe(23);
    expect(body.action).toBe("ask");
    expect(body.message).toBe("Какие боли?");
    expect(body.language).toBe("ru");
  });

  it("sends a null report id when no report is active", () => {
    const body = chatRequestBody(null, "market_scan", "доставка", {}, "en");
    expect(body.report_id).toBeNull();
  });

  it("builds human business-segment fallback options without placeholders", () => {
    const options = fallbackContentPlanOptions(active, "ru");
    const audiences = options.audiences.map((option) => option.value);
    expect(audiences.length).toBeGreaterThan(0);
    // No awkward "Клиенты ниши X" placeholder phrasing.
    expect(audiences.join(" ")).not.toContain("Клиенты ниши");
    expect(audiences).toContain("Владельцы интернет-магазинов");
    const channels = options.channels.map((option) => option.value);
    expect(channels).toEqual(["instagram", "telegram", "whatsapp", "website"]);
    expect(options.goals.length).toBeGreaterThan(0);
    expect(options.ctas.length).toBeGreaterThan(0);
    const all = JSON.stringify(options).toLowerCase();
    expect(all).not.toContain("прокладк");
  });

  it("localizes fallback options for en and kk", () => {
    expect(fallbackContentPlanOptions(active, "en").goals[0].value).toBe(
      "Get more leads",
    );
    expect(fallbackContentPlanOptions(active, "kk").goals[0].value).toBe(
      "Көбірек өтінім алу",
    );
  });
});
