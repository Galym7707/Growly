import { describe, expect, it } from "vitest";
import { isAuthRequired, isLocalAuthBypassAllowed } from "../lib/auth-config";

describe("auth configuration", () => {
  it("requires authentication in production even when the public flag is absent or false", () => {
    expect(isAuthRequired("production", undefined)).toBe(true);
    expect(isAuthRequired("production", "false")).toBe(true);
    expect(isLocalAuthBypassAllowed("production", "false")).toBe(false);
  });

  it("keeps local bypass available outside production unless auth is explicitly required", () => {
    expect(isAuthRequired("development", undefined)).toBe(false);
    expect(isAuthRequired("development", "false")).toBe(false);
    expect(isAuthRequired("development", "true")).toBe(true);
    expect(isLocalAuthBypassAllowed("development", undefined)).toBe(true);
    expect(isLocalAuthBypassAllowed("development", "true")).toBe(false);
  });
});
