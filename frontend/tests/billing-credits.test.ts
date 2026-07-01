import { describe, expect, it } from "vitest";
import {
  creditPacks,
  getCreditPack,
  isCreditPackId,
} from "../lib/billing/credits";

describe("video credit packs", () => {
  it("exposes packs with positive credit amounts and a product env key", () => {
    expect(creditPacks.length).toBeGreaterThan(0);
    for (const pack of creditPacks) {
      expect(pack.credits).toBeGreaterThan(0);
      expect(pack.productEnvKey).toMatch(/^POLAR_VIDEO_CREDITS_/);
    }
  });

  it("resolves and validates pack ids", () => {
    expect(isCreditPackId("video-10")).toBe(true);
    expect(isCreditPackId("nope")).toBe(false);
    expect(getCreditPack("video-30")?.credits).toBe(30);
    expect(getCreditPack("unknown")).toBeNull();
  });
});
