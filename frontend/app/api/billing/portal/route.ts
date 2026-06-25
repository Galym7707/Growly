import { NextRequest, NextResponse } from "next/server";
import {
  createPolarClient,
  getAppUrl,
  PORTAL_NOT_CONFIGURED_MESSAGE,
} from "@/lib/billing/polar";
import { getBillingStatus, getBillingUser } from "@/lib/billing/server";

export async function POST(request: NextRequest) {
  const user = await getBillingUser(request);
  if (!user) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const polar = createPolarClient();
  if (!polar) {
    return NextResponse.json(
      { detail: PORTAL_NOT_CONFIGURED_MESSAGE },
      { status: 400 },
    );
  }

  try {
    const billing = await getBillingStatus(user.id);
    const sessionRequest = billing.customerId
      ? { customerId: billing.customerId, returnUrl: `${getAppUrl(request)}/settings/billing` }
      : { externalCustomerId: user.id, returnUrl: `${getAppUrl(request)}/settings/billing` };

    const session = await polar.customerSessions.create(sessionRequest);
    return NextResponse.json({ url: session.customerPortalUrl });
  } catch {
    return NextResponse.json(
      { detail: PORTAL_NOT_CONFIGURED_MESSAGE },
      { status: 400 },
    );
  }
}
