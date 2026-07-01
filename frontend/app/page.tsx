/* eslint-disable @next/next/no-page-custom-font, @next/next/no-css-tags -- Keep the supplied landing assets isolated from workspace routes. */
import { readFileSync } from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import { LandingScripts } from "@/components/landing-scripts";

export const metadata: Metadata = {
  title: "Growly - AI Content Intelligence",
  description:
    "Growly tracks competitors, reads market signals, and turns them into a ready content plan.",
};

function readLandingMarkup(): string {
  const source = readFileSync(
    path.join(process.cwd(), "public", "landing", "index.html"),
    "utf8",
  );
  const body = source.match(/<body[^>]*>([\s\S]*?)<\/body>/i)?.[1];

  if (!body) {
    throw new Error("Landing page source does not contain a body element.");
  }

  return body.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
}

export default function LandingPage() {
  const markup = readLandingMarkup();

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Clash+Display:wght@500;600;700&family=Sora:wght@600;700;800&display=swap"
        rel="stylesheet"
      />
      <link rel="stylesheet" href="/landing/styles.css" />
      <div
        className="landing-static-page"
        dangerouslySetInnerHTML={{ __html: markup }}
      />
      <LandingScripts />
    </>
  );
}
