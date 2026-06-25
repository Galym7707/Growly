import { NextRequest, NextResponse } from "next/server";
import {
  createPolarClient,
  getPolarProductId,
  getReturnUrl,
  getSuccessUrl,
  PAYMENT_NOT_CONFIGURED_MESSAGE,
} from "@/lib/billing/polar";
import {
  getBillingUser,
  type BillingUser,
} from "@/lib/billing/server";
import {
  isPaidBillingPlan,
  normalizePlan,
  type BillingPlanId,
} from "@/lib/billing/plans";

export async function POST(request: NextRequest) {
  const user = await getBillingUser(request);
  if (!user) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const body = await parseBody(request);
  const plan = normalizePlan(body.plan);
  if (!isPaidBillingPlan(plan)) {
    return NextResponse.json({ detail: "Choose a paid plan." }, { status: 400 });
  }

  const productId = getPolarProductId(plan);
  const polar = createPolarClient();
  if (!productId || !polar) {
    return NextResponse.json(
      { detail: PAYMENT_NOT_CONFIGURED_MESSAGE },
      { status: 400 },
    );
  }

  try {
    const checkout = await polar.checkouts.create({
      products: [productId],
      successUrl: getSuccessUrl(request),
      returnUrl: getReturnUrl(request),
      customerEmail: user.email || undefined,
      externalCustomerId: user.id,
      metadata: checkoutMetadata(user, plan),
      customerMetadata: checkoutMetadata(user, plan),
    });

    return NextResponse.json({ url: checkout.url });
  } catch {
    return NextResponse.json(
      { detail: "Could not start checkout. Please try again." },
      { status: 502 },
    );
  }
}

async function parseBody(request: NextRequest): Promise<{ plan?: string }> {
  try {
    const value = await request.json();
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function checkoutMetadata(
  user: BillingUser,
  plan: BillingPlanId,
): Record<string, string> {
  return {
    userId: user.id,
    workspaceId: user.workspaceId || user.id,
    plan,
  };
}
