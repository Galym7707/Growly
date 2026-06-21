export type PlatformAccountStatus = {
  selected: boolean;
  account_id: string | null;
  account_name: string | null;
  available_count: number;
};

export type IntegrationsStatus = {
  telegram: { connected: boolean; channel_id?: string | null };
  notion: { connected: boolean; root_configured?: boolean };
  blotato: {
    enabled: boolean;
    connected: boolean;
    accounts_count: number;
    instagram?: PlatformAccountStatus | null;
  };
};

export type BlotatoStatus = {
  enabled: boolean;
  api_key_configured: boolean;
  connected: boolean;
  accounts_count: number;
  last_checked_at: string | null;
  instagram?: PlatformAccountStatus | null;
};

export type BlotatoAccount = {
  id: string;
  platform: string;
  name: string;
  display_name: string;
  connected: boolean;
};

export type BlotatoMapping = {
  platform: string;
  account_id: string | null;
  page_id?: string | null;
  enabled?: boolean;
};

export type PublishSubmission = {
  platform: string;
  post_submission_id: string | null;
  status: string;
  url?: string | null;
  error?: string | null;
};

export type PublishResult = {
  status: string;
  publication_ids: number[];
  blotato_submissions: PublishSubmission[];
};

export type ManualPackage = {
  id?: number;
  platform: string;
  caption: string | null;
  hook: string | null;
  script: string | null;
  visual_brief: string | null;
  hashtags: string | null;
  cta: string | null;
  status?: string;
};

export type PlatformMeta = {
  slug: string;
  label: string;
  provider: "telegram" | "blotato";
};

/** Platforms shown in publishing UI. Telegram uses the Bot API; the rest Blotato. */
export const PUBLISH_PLATFORMS: PlatformMeta[] = [
  { slug: "telegram", label: "Telegram", provider: "telegram" },
  { slug: "instagram", label: "Instagram", provider: "blotato" },
  { slug: "threads", label: "Threads", provider: "blotato" },
  { slug: "tiktok", label: "TikTok", provider: "blotato" },
  { slug: "youtube", label: "YouTube Shorts", provider: "blotato" },
  { slug: "facebook", label: "Facebook", provider: "blotato" },
  { slug: "linkedin", label: "LinkedIn", provider: "blotato" },
  { slug: "x", label: "X/Twitter", provider: "blotato" },
];

export const BLOTATO_PLATFORMS = PUBLISH_PLATFORMS.filter(
  (platform) => platform.provider === "blotato",
);

export function accountForPlatform(
  accounts: BlotatoAccount[],
  slug: string,
): BlotatoAccount | null {
  return (
    accounts.find(
      (account) => account.platform === slug && account.connected,
    ) ||
    accounts.find((account) => account.platform === slug) ||
    null
  );
}

export function platformConnected(
  accounts: BlotatoAccount[],
  slug: string,
): boolean {
  return accounts.some(
    (account) => account.platform === slug && account.connected,
  );
}

export function accountsForPlatform(
  accounts: BlotatoAccount[],
  slug: string,
): BlotatoAccount[] {
  return accounts.filter((account) => account.platform === slug);
}

export type PublishRequestBody = {
  platforms: string[];
  publish_now: boolean;
  scheduled_time: string | null;
  media_urls: string[];
  language: string;
};

export function publishRequestBody(
  platforms: string[],
  publishNow: boolean,
  scheduledTime: string | null,
  mediaUrls: string[],
  language: string,
): PublishRequestBody {
  return {
    platforms,
    publish_now: publishNow,
    scheduled_time: publishNow ? null : scheduledTime,
    media_urls: mediaUrls,
    language,
  };
}

export type ScheduleRequestBody = {
  platforms: string[];
  scheduled_time: string;
  media_urls: string[];
  language: string;
};

export function scheduleRequestBody(
  platforms: string[],
  scheduledTime: string,
  mediaUrls: string[],
  language: string,
): ScheduleRequestBody {
  return {
    platforms,
    scheduled_time: scheduledTime,
    media_urls: mediaUrls,
    language,
  };
}

/** Localized state label for a platform. Source RU strings are passed through `t`. */
export function platformStateLabel(
  status: IntegrationsStatus["blotato"] | null,
  accounts: BlotatoAccount[],
  slug: string,
): "connected" | "not_connected" | "disabled" {
  if (slug === "telegram") return "connected";
  if (!status || !status.enabled) return "disabled";
  return platformConnected(accounts, slug) ? "connected" : "not_connected";
}
