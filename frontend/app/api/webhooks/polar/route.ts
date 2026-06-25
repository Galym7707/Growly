import { validateEvent, WebhookVerificationError } from "@polar-sh/sdk/webhooks";
import { NextRequest, NextResponse } from "next/server";
import {
  completeBillingEvent,
  saveOrderFromPolar,
  saveSubscriptionFromPolar,
  startBillingEvent,
  type PolarOrderLike,
  type PolarSubscriptionLike,
} from "@/lib/billing/server";

export async function POST(request: NextRequest) {
  const webhookSecret = process.env.POLAR_WEBHOOK_SECRET?.trim();
  if (!webhookSecret) {
    return NextResponse.json(
      { detail: "Polar webhook is not configured." },
      { status: 400 },
    );
  }

  const body = await request.text();
  const headers = headersToRecord(request.headers);

  let payload: ReturnType<typeof validateEvent>;
  try {
    payload = validateEvent(body, headers, webhookSecret);
  } catch (error) {
    if (error instanceof WebhookVerificationError) {
      return NextResponse.json(
        { detail: "Invalid Polar webhook signature." },
        { status: 400 },
      );
    }
    return NextResponse.json(
      { detail: "Could not verify Polar webhook." },
      { status: 400 },
    );
  }

  const eventId =
    headers["webhook-id"] || headers["polar-event-id"] || headers["x-polar-event-id"] || null;
  const event = await startBillingEvent(payload, eventId);
  if (event.duplicate) {
    return NextResponse.json({ received: true, duplicate: true });
  }

  try {
    await processPolarPayload(payload);
    await completeBillingEvent(event.id);
    return NextResponse.json({ received: true });
  } catch {
    return NextResponse.json(
      { detail: "Could not process Polar webhook." },
      { status: 500 },
    );
  }
}

async function processPolarPayload(payload: ReturnType<typeof validateEvent>) {
  switch (payload.type) {
    case "order.created":
    case "order.paid":
    case "order.updated":
      await saveOrderFromPolar(payload.data as PolarOrderLike, payload);
      return;
    case "subscription.created":
    case "subscription.updated":
    case "subscription.active":
    case "subscription.canceled":
    case "subscription.revoked":
    case "subscription.uncanceled":
    case "subscription.past_due":
      await saveSubscriptionFromPolar(
        normalizeSubscriptionStatus(payload.data as PolarSubscriptionLike, payload.type),
      );
      return;
    case "checkout.created":
    case "checkout.updated":
    case "checkout.expired":
      return;
    default:
      return;
  }
}

function normalizeSubscriptionStatus(
  subscription: PolarSubscriptionLike,
  eventType: string,
): PolarSubscriptionLike {
  if (eventType === "subscription.revoked") {
    return { ...subscription, status: "revoked" };
  }
  if (eventType === "subscription.canceled") {
    return { ...subscription, status: subscription.status || "canceled" };
  }
  if (eventType === "subscription.past_due") {
    return { ...subscription, status: "past_due" };
  }
  return subscription;
}

function headersToRecord(headers: Headers): Record<string, string> {
  const record: Record<string, string> = {};
  headers.forEach((value, key) => {
    record[key.toLowerCase()] = value;
  });
  return record;
}
