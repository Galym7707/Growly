import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const landingHtml = readFileSync(
  path.join(frontendRoot, "public", "landing", "index.html"),
  "utf8",
);
const landingPage = readFileSync(
  path.join(frontendRoot, "app", "page.tsx"),
  "utf8",
);

describe("public landing page", () => {
  it("renders the supplied landing source at the root route", () => {
    expect(landingHtml).toContain('class="hero-h1 fade-up"');
    expect(landingHtml).toContain("Marketing plans and posts for your business.");
    expect(landingHtml).toContain("AI marketing workspace");
    expect(landingHtml).toContain('id="workflow"');
    expect(landingHtml).toContain('id="team"');
    expect(landingHtml).toContain('id="pricing"');
    expect(landingPage).toContain('public", "landing", "index.html"');
    expect(landingPage).toContain("<LandingScripts />");
  });

  it("keeps product entry points on the existing authentication routes", () => {
    expect(landingHtml).toContain('href="/login"');
    expect(landingHtml).toContain('href="/register"');
    expect(landingHtml).toContain('class="nav-login"');
    expect(landingHtml).toContain('class="nav-cta"');
    expect(landingHtml).toContain('class="hero-primary"');
    expect(landingHtml).toContain('href="/privacy"');
    expect(landingHtml).toContain('href="/terms"');
  });

  it("uses checkout buttons for paid pricing plans", () => {
    expect(landingHtml).toContain('data-checkout-plan="starter"');
    expect(landingHtml).toContain('data-checkout-plan="pro"');
    expect(landingHtml).toContain('data-checkout-plan="agency"');
    expect(landingHtml).toContain('pricing.free.name');
    expect(landingHtml).toContain('pricing.agency.name');
  });

  it("does not ship countdown or long dash copy", () => {
    expect(landingHtml).not.toMatch(/countdown|Early access|waitlist/i);
    expect(landingHtml).not.toContain("—");
    expect(landingHtml).not.toContain("вЂ”");
  });
});
