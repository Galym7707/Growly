import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  PUBLISH_PLATFORMS,
  accountForPlatform,
  platformConnected,
  platformStateLabel,
  publishRequestBody,
  scheduleRequestBody,
  type BlotatoAccount,
} from "../lib/integrations";
import { translate } from "../lib/i18n";

const accounts: BlotatoAccount[] = [
  { id: "1", platform: "instagram", name: "@brand", display_name: "Brand IG", connected: true },
  { id: "2", platform: "threads", name: "@brand", display_name: "Brand Threads", connected: true },
];

describe("social publishing helpers", () => {
  it("lists Telegram and all Blotato platforms", () => {
    const slugs = PUBLISH_PLATFORMS.map((p) => p.slug);
    expect(slugs).toEqual([
      "telegram",
      "instagram",
      "threads",
      "tiktok",
      "youtube",
      "facebook",
      "linkedin",
      "x",
    ]);
  });

  it("detects connected Instagram and Threads", () => {
    expect(platformConnected(accounts, "instagram")).toBe(true);
    expect(platformConnected(accounts, "threads")).toBe(true);
    expect(platformConnected(accounts, "tiktok")).toBe(false);
    expect(accountForPlatform(accounts, "instagram")?.display_name).toBe("Brand IG");
  });

  it("marks platforms disabled when Blotato is off", () => {
    expect(platformStateLabel({ enabled: false, connected: false, accounts_count: 0 }, accounts, "instagram")).toBe("disabled");
    expect(platformStateLabel({ enabled: true, connected: true, accounts_count: 2 }, accounts, "instagram")).toBe("connected");
    expect(platformStateLabel({ enabled: true, connected: true, accounts_count: 2 }, accounts, "tiktok")).toBe("not_connected");
  });

  it("builds a publish-now request body with no scheduled time", () => {
    const body = publishRequestBody(["instagram", "threads"], true, "2026-06-21T10:00", [], "ru");
    expect(body.platforms).toEqual(["instagram", "threads"]);
    expect(body.publish_now).toBe(true);
    expect(body.scheduled_time).toBeNull();
    expect(body.language).toBe("ru");
  });

  it("builds a schedule request body carrying scheduled_time", () => {
    const body = scheduleRequestBody(["instagram"], "2026-06-21T10:00:00+05:00", [], "ru");
    expect(body.scheduled_time).toBe("2026-06-21T10:00:00+05:00");
    expect(body.platforms).toEqual(["instagram"]);
  });

  it("translates integration labels to RU/EN/KK", () => {
    expect(translate("ru", "Опубликовать сейчас")).toBe("Опубликовать сейчас");
    expect(translate("en", "Опубликовать сейчас")).toBe("Publish now");
    expect(translate("kk", "Опубликовать сейчас")).toBe("Қазір жариялау");
    expect(translate("en", "Настроить публикацию")).toBe("Set up publishing");
  });

  it("does not reference the Blotato API key in the frontend lib", () => {
    const source = readFileSync(
      join(process.cwd(), "lib", "integrations.ts"),
      "utf8",
    );
    expect(source).not.toContain("BLOTATO_API_KEY");
    expect(source).not.toMatch(/blotato[-_]?api[-_]?key/i);
  });
});
