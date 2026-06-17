import { describe, expect, it } from "vitest";
import {
  contentPlanPathFromGeneratedResponse,
  extractGeneratedContentPlanId,
  extractGeneratedDraftId,
  extractGeneratedReportId,
  reportPathFromGeneratedResponse,
} from "../lib/generated-navigation";

describe("generated navigation helpers", () => {
  it("extracts report ids from supported API response shapes", () => {
    expect(extractGeneratedReportId({ report_id: "abc123" })).toBe("abc123");
    expect(extractGeneratedReportId({ id: 123 })).toBe("123");
    expect(extractGeneratedReportId({ reportId: "r-7" })).toBe("r-7");
    expect(extractGeneratedReportId({ report: { id: 7 } })).toBe("7");
    expect(reportPathFromGeneratedResponse({ report_id: "abc123" })).toBe(
      "/reports/abc123",
    );
  });

  it("returns null when a report id is absent", () => {
    expect(extractGeneratedReportId({ status: "completed", report: {} })).toBeNull();
    expect(reportPathFromGeneratedResponse({ status: "completed" })).toBeNull();
  });

  it("extracts content plan and draft ids for fallback routes", () => {
    expect(
      extractGeneratedContentPlanId({
        status: "completed",
        items: [{ id: 45 }],
      }),
    ).toBe("45");
    expect(extractGeneratedContentPlanId({ content_plan_id: "plan-1" })).toBe(
      "plan-1",
    );
    expect(contentPlanPathFromGeneratedResponse({ plan_id: 45 })).toBe(
      "/content-plan/45",
    );
    expect(extractGeneratedDraftId({ draft_id: 88 })).toBe("88");
    expect(extractGeneratedDraftId({ draft: { id: "draft-2" } })).toBe(
      "draft-2",
    );
  });
});
