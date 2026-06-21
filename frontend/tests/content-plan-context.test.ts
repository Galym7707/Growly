import { describe, expect, it } from "vitest";
import {
  buildActiveContextFromReport,
  contentPlanSubmitBody,
} from "../lib/active-context";

describe("content plan report context", () => {
  it("builds active context from a /reports payload", () => {
    const context = buildActiveContextFromReport({
      id: 23,
      title: "Анализ рынка: Логистика и доставка товаров",
      type: "market_scan",
      sources_count: 40,
      created_at: "2026-06-19T10:00:00+00:00",
      structure: {
        market_context: {
          topic: "Логистика и доставка товаров",
          region: "Казахстан",
          language: "ru",
        },
      },
    });
    expect(context?.report_id).toBe(23);
    expect(context?.topic).toBe("Логистика и доставка товаров");
    expect(context?.region).toBe("Казахстан");
    expect(context?.sources_count).toBe(40);
  });

  it("returns null for a payload without an id", () => {
    expect(buildActiveContextFromReport(null)).toBeNull();
    expect(buildActiveContextFromReport({ title: "no id" })).toBeNull();
  });

  it("includes the report id and chip selections in the submit body", () => {
    const body = contentPlanSubmitBody(
      23,
      {
        goal: "Получить заявки на доставку",
        audience: "владельцы интернет-магазинов",
        offer: "комплексная доставка",
        channels: ["telegram", "instagram"],
        contentTypes: ["post"],
        cta: "Оставить заявку",
        customInstruction: "спокойный тон",
      },
      "ru",
    );
    expect(body.report_id).toBe(23);
    expect(body.goal).toBe("Получить заявки на доставку");
    expect(body.weekly_objective).toContain("Получить заявки на доставку");
    expect(body.weekly_objective).toContain("спокойный тон");
    expect(body.business).toMatchObject({
      language: "ru",
      target_audience: "владельцы интернет-магазинов",
      preferred_channels: ["telegram", "instagram"],
    });
    expect(body.channels).toEqual(["telegram", "instagram"]);
    expect(body.content_types).toEqual(["post"]);
    expect(body.cta).toBe("Оставить заявку");
    expect(body.custom_instruction).toBe("спокойный тон");
    expect(body.language).toBe("ru");
  });

  it("carries a null report id for manual mode", () => {
    const body = contentPlanSubmitBody(
      null,
      {
        goal: "",
        audience: "",
        offer: "",
        channels: [],
        contentTypes: [],
        cta: "",
        customInstruction: "Просто несколько постов",
      },
      "en",
    );
    expect(body.report_id).toBeNull();
    expect(body.weekly_objective).toBe("Просто несколько постов");
    expect(body.custom_instruction).toBe("Просто несколько постов");
  });
});
