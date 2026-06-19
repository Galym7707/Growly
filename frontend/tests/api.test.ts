import { afterEach, describe, expect, it, vi } from "vitest";
import {
  apiErrorDebugInfo,
  apiRequest,
  buildApiUrl,
  sanitizeApiUrl,
} from "../lib/api";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("uses the existing Next proxy route so server-only API keys stay private", () => {
    expect(buildApiUrl("/content-plans")).toBe(
      "/api/growly/content-plans",
    );
    expect(buildApiUrl("/api/content-plans/45")).toBe(
      "/api/growly/content-plans/45",
    );
  });

  it("keeps debug URLs free of secret-like query values", () => {
    expect(
      sanitizeApiUrl(
        "https://backend.example.com/api/content-plans?token=abc&limit=40",
      ),
    ).toBe(
      "https://backend.example.com/api/content-plans?token=%5Bredacted%5D&limit=40",
    );
  });

  it("returns debug metadata for plain text 404 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("Not Found", { status: 404 })),
    );

    try {
      await apiRequest("/content-plans");
      throw new Error("Expected request to fail");
    } catch (value) {
      expect(apiErrorDebugInfo(value)).toEqual({
        message: "Not Found",
        status: 404,
        url: "/api/growly/content-plans",
      });
    }
  });

  it("returns debug metadata for network failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("Failed to fetch");
      }),
    );

    try {
      await apiRequest("/content-plans");
      throw new Error("Expected request to fail");
    } catch (value) {
      expect(apiErrorDebugInfo(value)).toEqual({
        message: "Failed to fetch",
        status: 0,
        url: "/api/growly/content-plans",
      });
    }
  });
});
