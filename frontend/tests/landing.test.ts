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
    expect(landingHtml).toContain('id="workflow"');
    expect(landingHtml).toContain('id="pricing"');
    expect(landingPage).toContain('public", "landing", "index.html"');
    expect(landingPage).toContain("<LandingScripts />");
  });

  it("keeps product entry points on the existing authentication routes", () => {
    expect(landingHtml).toContain('href="/login" class="nav-cta"');
    expect(readFileSync(path.join(frontendRoot, "public", "landing", "main.js"), "utf8"))
      .toContain("window.location.assign('/register')");
  });
});
