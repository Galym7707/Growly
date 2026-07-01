import { NextRequest, NextResponse } from "next/server";
import {
  createPolarClient,
  getCreditProductId,
  getReturnUrl,
  getSuccessUrl,
  PAYMENT_NOT_CONFIGURED_MESSAGE,
} from "@/lib/billing/polar";
import { getBillingUser, type BillingUser } from "@/lib/billing/server";
import { getCreditPack, isCreditPackId } from "@/lib/billing/credits";

export async function POST(request: NextRequest) {
  const user = await getBillingUser(request);
  if (!user) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const body = await parseBody(request);
  const packId = typeof body.pack === "string" ? body.pack : "";
  if (!isCreditPackId(packId)) {
    return NextResponse.json({ detail: "Choose a credit pack." }, { status: 400 });
  }
  const pack = getCreditPack(packId);
  const productId = getCreditProductId(packId);
  const polar = createPolarClient();
  if (!pack || !productId || !polar) {
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
      metadata: creditMetadata(user, packId, pack.credits),
      customerMetadata: creditMetadata(user, packId, pack.credits),
    });

    return NextResponse.json({ url: checkout.url });
  } catch {
    return NextResponse.json(
      { detail: "Could not start checkout. Please try again." },
      { status: 502 },
    );
  }
}

async function parseBody(request: NextRequest): Promise<{ pack?: string }> {
  try {
    const value = await request.json();
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function creditMetadata(
  user: BillingUser,
  pack: string,
  credits: number,
): Record<string, string> {
  return {
    userId: user.id,
    workspaceId: user.workspaceId || user.id,
    kind: "credits",
    pack,
    videoCredits: String(credits),
  };
}
