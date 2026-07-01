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
const landingScript = readFileSync(
  path.join(frontendRoot, "public", "landing", "main.js"),
  "utf8",
);

describe("public landing page", () => {
  it("renders the supplied landing source at the root route", () => {
    expect(landingHtml).toContain('class="hero-h1 fade-up"');
    expect(landingHtml).toContain("Market signals into ready content.");
    expect(landingHtml).toContain("MARKETING WORKSPACE");
    expect(landingHtml).toContain('id="workflow"');
    expect(landingHtml).toContain('id="stack"');
    expect(landingHtml).toContain('id="cases"');
    expect(landingHtml).toContain('id="pricing"');
    expect(landingPage).toContain('public", "landing", "index.html"');
    expect(landingPage).toContain("<LandingScripts />");
    expect(landingPage).toContain("Clash+Display");
  });

  it("keeps product entry points on the existing authentication routes", () => {
    expect(landingHtml).toContain('href="/login"');
    expect(landingHtml).toContain('href="/register"');
    expect(landingHtml).toContain('class="nav-login"');
    expect(landingHtml).toContain('class="nav-cta"');
    expect(landingHtml).toContain('class="swipe-cta"');
    expect(landingHtml).toContain('data-register-target="/register"');
    expect(landingHtml).toContain('href="/privacy"');
    expect(landingHtml).toContain('href="/terms"');
  });

  it("uses checkout buttons for paid pricing plans", () => {
    expect(landingHtml).toContain('data-checkout-plan="starter"');
    expect(landingHtml).toContain('data-checkout-plan="pro"');
    expect(landingHtml).toContain('data-checkout-plan="agency"');
    expect(landingHtml).toContain("pricing.starter.name");
    expect(landingHtml).toContain("pricing.growth.name");
    expect(landingHtml).toContain("pricing.scale.name");
  });

  it("keeps landing JavaScript connected to product routes", () => {
    expect(landingScript).toContain("fetch('/api/billing/checkout'");
    expect(landingScript).toContain("window.location.assign(`/register${query}`)");
    expect(landingScript).toContain("response.status === 401");
  });
});
