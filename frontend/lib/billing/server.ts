import "server-only";

import { createServerClient } from "@supabase/ssr";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { NextRequest } from "next/server";
import { isAuthRequired } from "@/lib/auth-config";
import {
  canPlanUseFeature,
  normalizePlan,
  type BillingFeature,
  type BillingPlanId,
} from "./plans";

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
type JsonRecord = Record<string, JsonValue>;

export type BillingUser = {
  id: string;
  email: string | null;
  workspaceId: string | null;
};

export type SubscriptionRow = {
  id: string;
  user_id: string;
  workspace_id: string | null;
  polar_customer_id: string | null;
  polar_subscription_id: string | null;
  polar_product_id: string | null;
  plan: string;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at: string;
};

export type BillingStatus = {
  plan: BillingPlanId;
  status: string;
  nextBillingDate: string | null;
  cancelAtPeriodEnd: boolean;
  customerId: string | null;
  subscriptionId: string | null;
};

export class SubscriptionRequiredError extends Error {
  status = 402;

  constructor(
    public feature: BillingFeature,
    message = "Upgrade is required for this feature.",
  ) {
    super(message);
  }
}

function supabaseUrl(): string | null {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ||
    process.env.SUPABASE_URL?.trim() ||
    null
  );
}

function supabaseAnonKey(): string | null {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() ||
    process.env.SUPABASE_PUBLISHABLE_API_KEY?.trim() ||
    null
  );
}

function supabaseSecretKey(): string | null {
  return (
    process.env.SUPABASE_SECRET_API_KEY?.trim() ||
    process.env.SUPABASE_SERVICE_ROLE_KEY?.trim() ||
    null
  );
}

export function isBillingDatabaseConfigured(): boolean {
  return Boolean(supabaseUrl() && supabaseSecretKey());
}

export function createBillingAdminClient(): SupabaseClient | null {
  const url = supabaseUrl();
  const secret = supabaseSecretKey();
  if (!url || !secret) return null;
  return createClient(url, secret, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

export async function getBillingUser(
  request: NextRequest,
): Promise<BillingUser | null> {
  if (!isAuthRequired()) {
    return {
      id: "local",
      email: "local@growly.test",
      workspaceId: "local",
    };
  }

  const url = supabaseUrl();
  const anon = supabaseAnonKey();
  if (!url || !anon) return null;

  const supabase = createServerClient(url, anon, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll() {
        // Session refresh is handled by frontend/proxy.ts.
      },
    },
  });

  const { data } = await supabase.auth.getUser();
  if (!data.user) return null;
  return {
    id: data.user.id,
    email: data.user.email ?? null,
    workspaceId: data.user.id,
  };
}

export async function getCurrentUserPlan(userId: string): Promise<BillingPlanId> {
  const subscription = await getActiveSubscription(userId);
  return normalizePlan(subscription?.plan);
}

export async function canUseFeature(
  userId: string,
  feature: BillingFeature,
): Promise<boolean> {
  const plan = await getCurrentUserPlan(userId);
  return canPlanUseFeature(plan, feature);
}

export async function requireSubscription(
  userId: string,
  feature: BillingFeature,
): Promise<void> {
  if (await canUseFeature(userId, feature)) return;
  throw new SubscriptionRequiredError(feature);
}

export async function getBillingStatus(
  userId: string,
): Promise<BillingStatus> {
  const subscription = await getActiveSubscription(userId);
  return {
    plan: normalizePlan(subscription?.plan),
    status: subscription?.status || "free",
    nextBillingDate: subscription?.current_period_end || null,
    cancelAtPeriodEnd: Boolean(subscription?.cancel_at_period_end),
    customerId: subscription?.polar_customer_id || null,
    subscriptionId: subscription?.polar_subscription_id || null,
  };
}

export async function getActiveSubscription(
  userId: string,
): Promise<SubscriptionRow | null> {
  const supabase = createBillingAdminClient();
  if (!supabase) return null;

  const { data, error } = await supabase
    .from("subscriptions")
    .select("*")
    .eq("user_id", userId)
    .in("status", ["active", "trialing", "past_due", "unpaid", "canceled"])
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) return null;
  return (data as SubscriptionRow | null) || null;
}

export type PolarSubscriptionLike = {
  id: string;
  customerId?: string | null;
  productId?: string | null;
  status?: string | null;
  currentPeriodStart?: Date | string | null;
  currentPeriodEnd?: Date | string | null;
  cancelAtPeriodEnd?: boolean | null;
  metadata?: Record<string, unknown> | null;
  customer?: {
    id?: string | null;
    externalId?: string | null;
    metadata?: Record<string, unknown> | null;
  } | null;
};

export type PolarOrderLike = {
  id: string;
  customerId?: string | null;
  productId?: string | null;
  subscriptionId?: string | null;
  checkoutId?: string | null;
  totalAmount?: number | null;
  currency?: string | null;
  status?: string | null;
  paid?: boolean | null;
  metadata?: Record<string, unknown> | null;
  customer?: {
    id?: string | null;
    externalId?: string | null;
    metadata?: Record<string, unknown> | null;
  } | null;
};

export function resolveUserIdFromPolarObject(
  value: PolarSubscriptionLike | PolarOrderLike,
): string | null {
  return (
    metadataString(value.metadata, "userId") ||
    metadataString(value.customer?.metadata, "userId") ||
    safeString(value.customer?.externalId)
  );
}

export function resolveWorkspaceIdFromPolarObject(
  value: PolarSubscriptionLike | PolarOrderLike,
): string | null {
  return (
    metadataString(value.metadata, "workspaceId") ||
    metadataString(value.customer?.metadata, "workspaceId")
  );
}

export function resolvePlanFromPolarObject(
  value: PolarSubscriptionLike | PolarOrderLike,
): BillingPlanId {
  return normalizePlan(
    metadataString(value.metadata, "plan") ||
      metadataString(value.customer?.metadata, "plan"),
  );
}

export async function saveSubscriptionFromPolar(
  subscription: PolarSubscriptionLike,
): Promise<void> {
  const supabase = createBillingAdminClient();
  const userId = resolveUserIdFromPolarObject(subscription);
  if (!supabase || !userId) return;

  const workspaceId = resolveWorkspaceIdFromPolarObject(subscription);
  const row = {
    user_id: userId,
    workspace_id: workspaceId,
    polar_customer_id:
      safeString(subscription.customerId) || safeString(subscription.customer?.id),
    polar_subscription_id: subscription.id,
    polar_product_id: safeString(subscription.productId),
    plan: resolvePlanFromPolarObject(subscription),
    status: safeString(subscription.status) || "active",
    current_period_start: toIso(subscription.currentPeriodStart),
    current_period_end: toIso(subscription.currentPeriodEnd),
    cancel_at_period_end: Boolean(subscription.cancelAtPeriodEnd),
    updated_at: new Date().toISOString(),
  };

  const existing = await findSubscription(supabase, {
    polarSubscriptionId: subscription.id,
    userId,
    workspaceId,
  });

  if (existing) {
    await supabase.from("subscriptions").update(row).eq("id", existing.id);
    return;
  }

  await supabase.from("subscriptions").insert(row);
}

export async function saveOrderFromPolar(
  order: PolarOrderLike,
  rawEvent: unknown,
): Promise<void> {
  const supabase = createBillingAdminClient();
  const userId = resolveUserIdFromPolarObject(order);
  if (!supabase || !userId) return;

  const row = {
    user_id: userId,
    polar_order_id: order.id,
    polar_customer_id: safeString(order.customerId) || safeString(order.customer?.id),
    polar_product_id: safeString(order.productId),
    amount: order.totalAmount ?? null,
    currency: safeString(order.currency),
    status: order.paid ? "paid" : safeString(order.status) || "created",
    raw_event: sanitizeJson(rawEvent),
    updated_at: new Date().toISOString(),
  };

  const { data: existing } = await supabase
    .from("payments")
    .select("id")
    .eq("polar_order_id", order.id)
    .maybeSingle();

  if (existing?.id) {
    await supabase.from("payments").update(row).eq("id", existing.id);
    return;
  }

  await supabase.from("payments").insert(row);
}

export async function startBillingEvent(
  payload: { type?: string; data?: unknown },
  eventId: string | null,
): Promise<{ id: string | null; duplicate: boolean }> {
  const supabase = createBillingAdminClient();
  if (!supabase) return { id: null, duplicate: false };

  if (eventId) {
    const { data: existing } = await supabase
      .from("billing_events")
      .select("id, processed")
      .eq("provider", "polar")
      .eq("event_id", eventId)
      .maybeSingle();
    if (existing?.processed) {
      return { id: existing.id as string, duplicate: true };
    }
    if (existing?.id) {
      return { id: existing.id as string, duplicate: false };
    }
  }

  const polarObject =
    payload.data && typeof payload.data === "object"
      ? (payload.data as PolarSubscriptionLike | PolarOrderLike)
      : null;
  const userId = polarObject ? resolveUserIdFromPolarObject(polarObject) : null;
  const workspaceId = polarObject
    ? resolveWorkspaceIdFromPolarObject(polarObject)
    : null;

  const { data } = await supabase
    .from("billing_events")
    .insert({
      provider: "polar",
      event_id: eventId,
      event_type: payload.type || "unknown",
      user_id: userId,
      workspace_id: workspaceId,
      processed: false,
      payload: sanitizeJson(payload),
    })
    .select("id")
    .single();

  return { id: (data?.id as string | undefined) || null, duplicate: false };
}

export async function completeBillingEvent(eventRowId: string | null) {
  const supabase = createBillingAdminClient();
  if (!supabase || !eventRowId) return;
  await supabase
    .from("billing_events")
    .update({ processed: true })
    .eq("id", eventRowId);
}

async function findSubscription(
  supabase: SupabaseClient,
  query: {
    polarSubscriptionId: string;
    userId: string;
    workspaceId: string | null;
  },
): Promise<{ id: string } | null> {
  const { data: byPolar } = await supabase
    .from("subscriptions")
    .select("id")
    .eq("polar_subscription_id", query.polarSubscriptionId)
    .maybeSingle();
  if (byPolar?.id) return { id: byPolar.id as string };

  let builder = supabase
    .from("subscriptions")
    .select("id")
    .eq("user_id", query.userId)
    .limit(1);

  builder = query.workspaceId
    ? builder.eq("workspace_id", query.workspaceId)
    : builder.is("workspace_id", null);

  const { data: byUser } = await builder.maybeSingle();
  return byUser?.id ? { id: byUser.id as string } : null;
}

function metadataString(
  metadata: Record<string, unknown> | null | undefined,
  key: string,
): string | null {
  if (!metadata) return null;
  return safeString(metadata[key]);
}

function safeString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function toIso(value: Date | string | null | undefined): string | null {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString();
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? null : parsed.toISOString();
}

export function sanitizeJson(value: unknown): JsonValue {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return value.toISOString();
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (Array.isArray(value)) return value.map((item) => sanitizeJson(item));
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).reduce<JsonRecord>(
      (result, [key, item]) => {
        result[key] = sanitizeJson(item);
        return result;
      },
      {},
    );
  }
  return String(value);
}
