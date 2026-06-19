import { describe, expect, it } from "vitest";
import { reportSections, shortConclusion } from "../lib/report-sections";

describe("report sections", () => {
  it("splits a market-scan structure into ordered sections", () => {
    const structure = {
      executive_summary: "Краткий вывод.",
      audience_pains: ["Долгая доставка", "Нет трекинга"],
      repeated_offers: ["Бесплатная доставка"],
      content_gaps: ["Нет кейсов"],
      weekly_priorities: ["Снять видео-отзыв"],
      dominant_topics: ["Сроки доставки"],
    };
    const sections = reportSections(structure);
    const keys = sections.map((section) => section.key);

    expect(keys).toContain("audience_pains");
    expect(keys).toContain("repeated_offers");
    expect(keys).toContain("content_gaps");
    expect(keys).toContain("weekly");
    // "Боли клиентов" comes before "Что сделать на этой неделе".
    expect(keys.indexOf("audience_pains")).toBeLessThan(keys.indexOf("weekly"));
    const pains = sections.find((section) => section.key === "audience_pains");
    expect(pains?.items).toEqual(["Долгая доставка", "Нет трекинга"]);
  });

  it("maps competitor-report synonyms to the same sections", () => {
    const sections = reportSections({
      repeating_offers: ["Подписка"],
      actions_this_week: ["Опубликовать кейс"],
    });
    const offers = sections.find((section) => section.key === "repeated_offers");
    const weekly = sections.find((section) => section.key === "weekly");
    expect(offers?.items).toEqual(["Подписка"]);
    expect(weekly?.items).toEqual(["Опубликовать кейс"]);
  });

  it("omits empty sections", () => {
    expect(reportSections({})).toEqual([]);
    expect(reportSections({ audience_pains: [] })).toEqual([]);
  });

  it("clamps a long conclusion so report lists avoid huge paragraphs", () => {
    const long =
      "Первое предложение про рынок. Второе предложение про конкурентов. " +
      "Третье предложение про боли. Четвёртое предложение про офферы. " +
      "Пятое предложение про пробелы. Шестое предложение про риски.";
    const short = shortConclusion(long, 3);
    expect(short.length).toBeLessThan(long.length);
    expect(short.split(/[.!?]+/).filter((part) => part.trim()).length).toBe(3);
    expect(short).toContain("Первое предложение про рынок");
    expect(short).not.toContain("Шестое предложение");
  });

  it("returns an empty string for missing summaries", () => {
    expect(shortConclusion(null)).toBe("");
    expect(shortConclusion("   ")).toBe("");
  });
});
