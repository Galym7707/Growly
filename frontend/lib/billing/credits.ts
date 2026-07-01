// Video credit packs for pay-per-video AI generation (Replicate provider).
//
// Each pack maps to a one-time Polar product. The product id is read from the
// env var named by `productEnvKey`; a pack is only offered when that id is set.
// Credits are granted by the Polar webhook when the order is paid and consumed
// by the backend when a Replicate video is generated.

export type CreditPackId = "video-10" | "video-30" | "video-100";

export type CreditPack = {
  id: CreditPackId;
  credits: number;
  price: string;
  productEnvKey: string;
};

export const creditPacks: CreditPack[] = [
  {
    id: "video-10",
    credits: 10,
    price: "$9",
    productEnvKey: "POLAR_VIDEO_CREDITS_10_PRODUCT_ID",
  },
  {
    id: "video-30",
    credits: 30,
    price: "$24",
    productEnvKey: "POLAR_VIDEO_CREDITS_30_PRODUCT_ID",
  },
  {
    id: "video-100",
    credits: 100,
    price: "$69",
    productEnvKey: "POLAR_VIDEO_CREDITS_100_PRODUCT_ID",
  },
];

export function getCreditPack(id: string): CreditPack | null {
  return creditPacks.find((pack) => pack.id === id) || null;
}

export function isCreditPackId(value: string): value is CreditPackId {
  return creditPacks.some((pack) => pack.id === value);
}
