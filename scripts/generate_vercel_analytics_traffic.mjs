import { chromium, devices } from "playwright";
import fs from "node:fs";
import path from "node:path";

const visits = Number.parseInt(process.env.TEST_VISIT_COUNT || "100", 10);
const baseUrl = normalizeBaseUrl(
  process.env.TEST_SITE_URL || process.argv[2] || "",
);
const headless = process.env.TEST_HEADLESS !== "false";
const pauseMs = Number.parseInt(process.env.TEST_VISIT_PAUSE_MS || "1400", 10);
const concurrency = Number.parseInt(process.env.TEST_VISIT_CONCURRENCY || "5", 10);
const routes = (
  process.env.TEST_VISIT_ROUTES || "/,/login?mode=register,/login,/privacy,/terms"
)
  .split(",")
  .map((route) => route.trim())
  .filter(Boolean);

if (!baseUrl) {
  throw new Error("Pass TEST_SITE_URL or the site URL as the first argument.");
}
if (!Number.isInteger(visits) || visits < 1 || visits > 1000) {
  throw new Error("TEST_VISIT_COUNT must be an integer from 1 to 1000.");
}
if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 20) {
  throw new Error("TEST_VISIT_CONCURRENCY must be an integer from 1 to 20.");
}

const browser = await chromium.launch({ headless });
const profiles = [
  devices["Desktop Chrome"],
  devices["Desktop Edge"],
  devices["iPhone 15"],
  devices["Pixel 7"],
  devices["iPad Pro 11"],
];
const results = [];

try {
  let nextVisit = 0;
  await Promise.all(
    Array.from({ length: concurrency }, async () => {
      while (nextVisit < visits) {
        const index = nextVisit;
        nextVisit += 1;
        results.push(await runVisit(browser, index));
      }
    }),
  );
} finally {
  await browser.close();
}

const outputDir = path.join(process.cwd(), "logs");
fs.mkdirSync(outputDir, { recursive: true });
const outputPath = path.join(outputDir, "vercel-analytics-test-traffic.json");
fs.writeFileSync(
  outputPath,
  JSON.stringify(
    {
      created_at: new Date().toISOString(),
      base_url: baseUrl,
      visits_requested: visits,
      ok: results.filter((result) => result.ok).length,
      failed: results.filter((result) => !result.ok).length,
      results,
    },
    null,
    2,
  ),
);

console.log(`wrote ${outputPath}`);

function normalizeBaseUrl(value) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return trimmed.endsWith("/") ? trimmed : `${trimmed}/`;
}

async function runVisit(browser, index) {
  const route = routes[index % routes.length];
  const url = new URL(route, baseUrl).toString();
  const profile = profiles[index % profiles.length];
  const context = await browser.newContext({
    ...profile,
    locale: index % 3 === 0 ? "ru-KZ" : index % 3 === 1 ? "kk-KZ" : "en-US",
    timezoneId: "Asia/Almaty",
  });
  const page = await context.newPage();
  const started = Date.now();

  try {
    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 30_000,
    });
    await page.waitForLoadState("load", { timeout: 15_000 }).catch(() => {});
    await page.waitForTimeout(pauseMs);
    console.log(
      `${String(index + 1).padStart(3, "0")}/${visits} ${response?.status() || "n/a"} ${url}`,
    );
    return {
      visit: index + 1,
      url,
      status: response?.status() || null,
      ok: response?.ok() || false,
      ms: Date.now() - started,
    };
  } catch (error) {
    console.error(`${String(index + 1).padStart(3, "0")}/${visits} failed ${url}`);
    return {
      visit: index + 1,
      url,
      status: null,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
      ms: Date.now() - started,
    };
  } finally {
    await context.close();
  }
}
