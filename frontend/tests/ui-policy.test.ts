import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

function files(root: string): string[] {
  return readdirSync(root).flatMap((name) => {
    const path = join(root, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

const sourceFiles = [
  ...files(join(process.cwd(), "app")),
  ...files(join(process.cwd(), "components")),
].filter((path) => /\.(css|ts|tsx)$/.test(path));

describe("Growly UI policy", () => {
  it("contains no emoji glyphs in interface source", () => {
    const violations = sourceFiles.filter((path) =>
      /\p{Extended_Pictographic}/u.test(readFileSync(path, "utf8")),
    );
    expect(violations).toEqual([]);
  });

  it("contains no purple or pink decorative gradients", () => {
    const violations = sourceFiles.filter((path) =>
      /(purple|pink|linear-gradient|radial-gradient)/i.test(
        readFileSync(path, "utf8"),
      ),
    );
    expect(violations).toEqual([]);
  });

  it("does not expose server credentials through public environment names", () => {
    const clientSource = sourceFiles
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");
    expect(clientSource).not.toMatch(
      /NEXT_PUBLIC_(?:GROWLY_API_KEY|SUPABASE_SERVICE_ROLE_KEY|NOTION_API_KEY|TELEGRAM_BOT_API_KEY|GROQ_API_KEY|TAVILY_API_KEY)/,
    );
  });
});
