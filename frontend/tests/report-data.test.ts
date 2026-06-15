import { describe, expect, it } from "vitest";
import {
  asCompetitors,
  asMetricRows,
  asStrings,
} from "../lib/report-data";
import { formatReportTitle } from "../lib/api";

describe("report data normalization", () => {
  it("renders structured competitor report rows from mock JSON", () => {
    const report = {
      competitors: [
        {
          competitor: "Example",
          channel: "Website",
          offer: "Consulting",
          opportunity: "Clearer onboarding",
        },
      ],
      content_gaps: ["Pricing explanation", "Case studies"],
    };

    expect(asCompetitors(report.competitors)).toHaveLength(1);
    expect(asCompetitors(report.competitors)[0].opportunity).toBe(
      "Clearer onboarding",
    );
    expect(asStrings(report.content_gaps)).toEqual([
      "Pricing explanation",
      "Case studies",
    ]);
  });

  it("ignores invalid chart rows instead of inventing metrics", () => {
    expect(asMetricRows(undefined)).toEqual([]);
    expect(asMetricRows(["invalid", null])).toEqual([]);
  });

  it("localizes legacy English report titles", () => {
    expect(
      formatReportTitle(
        "Competitor report: latest evidence",
        "competitor_report",
      ),
    ).toBe("Конкурентный отчёт");
  });
});
