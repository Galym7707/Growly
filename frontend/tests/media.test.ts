import { describe, expect, it } from "vitest";
import {
  isAllowedMediaFile,
  mediaKind,
  mergeMedia,
  visualStatusLabel,
} from "../lib/media";

describe("media helpers", () => {
  it("accepts supported image and video files", () => {
    expect(isAllowedMediaFile({ name: "photo.jpg", type: "image/jpeg" })).toBe(true);
    expect(isAllowedMediaFile({ name: "clip.mp4", type: "video/mp4" })).toBe(true);
    expect(isAllowedMediaFile({ name: "document.pdf", type: "application/pdf" })).toBe(false);
  });

  it("detects video URLs", () => {
    expect(mediaKind("https://cdn.example/clip.mp4?token=1")).toBe("video");
    expect(mediaKind("https://cdn.example/photo.jpg")).toBe("image");
  });

  it("deduplicates and limits attached media", () => {
    const first = { url: "one", kind: "image" as const, name: "one.jpg" };
    const second = { url: "two", kind: "video" as const, name: "two.mp4" };
    expect(mergeMedia([first], [first, second], 2)).toEqual([first, second]);
  });

  it("localizes provider progress states", () => {
    expect(visualStatusLabel("generating-media")).toBe("Генерация медиа");
  });
});
