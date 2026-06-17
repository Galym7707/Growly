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

  it("uses NEXT_PUBLIC_GROWLY_API_URL for backend /api endpoints", () => {
    expect(buildApiUrl("/content-plans", "https://backend.example.com")).toBe(
      "https://backend.example.com/api/content-plans",
    );
    expect(
      buildApiUrl("/api/content-plans/45", "https://backend.example.com/api"),
    ).toBe("https://backend.example.com/api/content-plans/45");
  });

  it("falls back only to the existing Next proxy route when no backend URL is set", () => {
    expect(buildApiUrl("/content-plans", "")).toBe(
      "/api/growly/content-plans",
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
    vi.stubEnv("NEXT_PUBLIC_GROWLY_API_URL", "https://backend.example.com");
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
        url: "https://backend.example.com/api/content-plans",
      });
    }
  });

  it("returns debug metadata for network failures", async () => {
    vi.stubEnv("NEXT_PUBLIC_GROWLY_API_URL", "https://backend.example.com");
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
        url: "https://backend.example.com/api/content-plans",
      });
    }
  });
});
