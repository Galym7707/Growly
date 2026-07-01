import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const reportPage = readFileSync(
  path.join(frontendRoot, "app", "(workspace)", "reports", "[id]", "page.tsx"),
  "utf8",
);

describe("report page localization", () => {
  it("requests the report payload for the active locale", () => {
    expect(reportPage).toContain(
      "`/reports/${params.id}?language=${encodeURIComponent(locale)}`",
    );
    expect(reportPage).toContain("}, [locale, params.id, t]);");
  });
});
