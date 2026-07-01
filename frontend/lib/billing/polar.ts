import "server-only";

import { Polar } from "@polar-sh/sdk";
import type { NextRequest } from "next/server";
import {
  getBillingPlan,
  isPaidBillingPlan,
  type BillingPlanId,
  type PaidBillingPlanId,
} from "./plans";
import { creditPacks, getCreditPack, type CreditPack } from "./credits";

export const PAYMENT_NOT_CONFIGURED_MESSAGE = "Payment is not configured yet.";
export const PORTAL_NOT_CONFIGURED_MESSAGE =
  "Billing portal is not configured yet.";

export function getPolarServer(): "sandbox" | "production" {
  return process.env.POLAR_SERVER === "production" ? "production" : "sandbox";
}

export function getPolarAccessToken(): string | null {
  return process.env.POLAR_ACCESS_TOKEN?.trim() || null;
}

export function createPolarClient(): Polar | null {
  const accessToken = getPolarAccessToken();
  if (!accessToken) return null;
  return new Polar({
    accessToken,
    server: getPolarServer(),
  });
}

export function getPolarProductId(plan: BillingPlanId): string | null {
  if (!isPaidBillingPlan(plan)) return null;
  const envKey = getBillingPlan(plan).productEnvKey;
  if (!envKey) return null;
  return process.env[envKey]?.trim() || null;
}

export function getConfiguredPaidPlans(): Record<PaidBillingPlanId, boolean> {
  return {
    starter: Boolean(getPolarProductId("starter")),
    pro: Boolean(getPolarProductId("pro")),
    agency: Boolean(getPolarProductId("agency")),
  };
}

export function getCreditProductId(packId: string): string | null {
  const pack = getCreditPack(packId);
  if (!pack) return null;
  return process.env[pack.productEnvKey]?.trim() || null;
}

export type ConfiguredCreditPack = CreditPack & { configured: boolean };

export function getConfiguredCreditPacks(): ConfiguredCreditPack[] {
  return creditPacks.map((pack) => ({
    ...pack,
    configured: Boolean(process.env[pack.productEnvKey]?.trim()),
  }));
}

/** Credits granted for a paid Polar product id, or 0 if it is not a pack. */
export function resolveCreditsForProduct(productId: string | null): number {
  if (!productId) return 0;
  const pack = creditPacks.find(
    (item) => process.env[item.productEnvKey]?.trim() === productId,
  );
  return pack ? pack.credits : 0;
}

export function getAppUrl(request?: NextRequest): string {
  const configured = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");

  const forwardedHost = request?.headers.get("x-forwarded-host");
  const forwardedProto = request?.headers.get("x-forwarded-proto");
  if (forwardedHost) {
    return `${forwardedProto || "https"}://${forwardedHost}`;
  }

  if (request?.nextUrl.origin) return request.nextUrl.origin;
  return "http://localhost:3000";
}

export function getSuccessUrl(request: NextRequest): string {
  const configured = process.env.POLAR_SUCCESS_URL?.trim();
  if (configured) return configured;
  return `${getAppUrl(request)}/settings/billing?checkout=success&checkout_id={CHECKOUT_ID}`;
}

export function getReturnUrl(request: NextRequest): string {
  const configured =
    process.env.POLAR_CANCEL_URL?.trim() || process.env.POLAR_SUCCESS_URL?.trim();
  if (configured) return configured;
  return `${getAppUrl(request)}/settings/billing`;
}
