import { NextRequest, NextResponse } from "next/server";
import { getConfiguredPaidPlans } from "@/lib/billing/polar";
import { getBillingStatus, getBillingUser } from "@/lib/billing/server";

export async function GET(request: NextRequest) {
  const user = await getBillingUser(request);
  if (!user) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const billing = await getBillingStatus(user.id);
  return NextResponse.json({
    ...billing,
    configuredPlans: getConfiguredPaidPlans(),
  });
}
