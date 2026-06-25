import { describe, expect, it } from "vitest";
import {
  billingPlans,
  canPlanUseFeature,
  getBillingPlan,
  normalizePlan,
  paidBillingPlanIds,
  requiredPlanForFeature,
} from "../lib/billing/plans";

describe("billing plans", () => {
  it("defines the requested Growly tiers and product env keys", () => {
    expect(billingPlans.map((plan) => plan.id)).toEqual([
      "free",
      "starter",
      "pro",
      "agency",
    ]);
    expect(getBillingPlan("starter").productEnvKey).toBe(
      "POLAR_STARTER_PRODUCT_ID",
    );
    expect(getBillingPlan("pro").productEnvKey).toBe("POLAR_PRO_PRODUCT_ID");
    expect(getBillingPlan("agency").productEnvKey).toBe(
      "POLAR_AGENCY_PRODUCT_ID",
    );
  });

  it("keeps paid plan ids aligned with checkout-supported plans", () => {
    expect(paidBillingPlanIds).toEqual(["starter", "pro", "agency"]);
    for (const plan of billingPlans) {
      expect(plan.features.length).toBeGreaterThanOrEqual(5);
      expect(plan.features.length).toBeLessThanOrEqual(7);
    }
  });

  it("normalizes unknown plans to free and gates paid features", () => {
    expect(normalizePlan("unknown")).toBe("free");
    expect(normalizePlan("pro")).toBe("pro");
    expect(canPlanUseFeature("free", "team:invite")).toBe(false);
    expect(canPlanUseFeature("starter", "team:invite")).toBe(true);
    expect(canPlanUseFeature("pro", "publishing:auto")).toBe(true);
    expect(requiredPlanForFeature("workspaces:agency").id).toBe("agency");
  });
});
