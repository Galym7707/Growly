export type MediaKind = "image" | "video";

export type AttachedMedia = {
  url: string;
  kind: MediaKind;
  name: string;
};

export const MEDIA_ACCEPT =
  ".jpg,.jpeg,.png,.webp,.gif,.mp4,.mov,.webm,image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime,video/webm";

const ALLOWED_MEDIA_TYPES = new Set([
  "image/gif",
  "image/jpeg",
  "image/png",
  "image/webp",
  "video/mp4",
  "video/quicktime",
  "video/webm",
]);

export function isAllowedMediaFile(file: Pick<File, "name" | "type">): boolean {
  if (ALLOWED_MEDIA_TYPES.has(file.type.toLowerCase())) return true;
  return /\.(gif|jpe?g|mov|mp4|png|webm|webp)$/i.test(file.name);
}

export function mediaKind(value: string, mimeType = ""): MediaKind {
  if (mimeType.toLowerCase().startsWith("video/")) return "video";
  return /\.(mov|mp4|webm)(?:$|[?#])/i.test(value) ? "video" : "image";
}

export function mergeMedia(
  current: AttachedMedia[],
  incoming: AttachedMedia[],
  limit = 10,
): AttachedMedia[] {
  const byUrl = new Map(current.map((item) => [item.url, item]));
  incoming.forEach((item) => {
    if (item.url) byUrl.set(item.url, item);
  });
  return Array.from(byUrl.values()).slice(0, limit);
}

export function visualStatusLabel(status: string): string {
  if (status === "queueing") return "В очереди";
  if (status === "generating-script" || status === "script-ready") {
    return "Подготовка сценария";
  }
  if (status === "generating-media" || status === "media-ready") {
    return "Генерация медиа";
  }
  if (status === "exporting") return "Экспорт медиа";
  return status;
}
