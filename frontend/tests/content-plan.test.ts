import { describe, expect, it } from "vitest";
import {
  formatContentStatus,
  formatContentType,
  sourceDisplay,
} from "../lib/content-plan";

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
});
