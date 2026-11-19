import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "../proxy";

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: { getUser: async () => ({ data: { user: null } }) },
  }),
}));

describe("production middleware access", () => {
  beforeEach(() => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "public-test-key");
  });

  afterEach(() => vi.unstubAllEnvs());

  it.each([
    ["/api/growly/auth/register", "POST"],
    ["/api/growly/share-links/test-token", "GET"],
    ["/api/growly/invitations/test-token", "GET"],
  ])("allows anonymous %s %s to reach the backend", async (path, method) => {
    const response = await proxy(new NextRequest(`https://growly.test${path}`, { method }));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it.each([
    ["/api/growly/dashboard", "GET"],
    ["/api/growly/auth/register", "GET"],
    ["/api/growly/share-links/test-token", "POST"],
    ["/api/growly/invitations/test-token/accept", "POST"],
    ["/api/growly/share-links", "GET"],
    ["/api/growly/auth/register/extra", "POST"],
  ])("keeps anonymous %s %s protected", async (path, method) => {
    const response = await proxy(new NextRequest(`https://growly.test${path}`, { method }));
    expect(response.status).toBe(401);
  });
});
