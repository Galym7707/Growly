import { describe, expect, it } from "vitest";
import {
  billingPlans,
  canPlanUseFeature,
  getBillingPlan,
  getBillingPlanDisplay,
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
    expect(getBillingPlan("pro").name).toBe("Growth");
    expect(getBillingPlan("agency").name).toBe("Custom");
    expect(getBillingPlan("agency").price).toBe("—");
  });

  it("keeps paid plan ids aligned with checkout-supported plans", () => {
    expect(paidBillingPlanIds).toEqual(["starter", "pro", "agency"]);
    for (const plan of billingPlans) {
      expect(plan.features.length).toBeGreaterThanOrEqual(3);
      expect(plan.features.length).toBeLessThanOrEqual(5);
    }
  });

  it("matches dashboard plan copy to the public pricing cards", () => {
    const starter = getBillingPlanDisplay("starter", "ru");
    const growth = getBillingPlanDisplay("pro", "ru");
    const custom = getBillingPlanDisplay("agency", "ru");

    expect(starter.features).toEqual([
      "5 источников конкурентов",
      "Еженедельный контент-план",
      "8 черновиков в месяц",
    ]);
    expect(starter.unavailableFeatures).toEqual(["Интеграция с CRM"]);
    expect(growth.name).toBe("Growth");
    expect(growth.features).toEqual([
      "25 источников конкурентов",
      "Безлимит черновиков",
      "Кейс-машина для CRM",
      "Еженедельные отчёты по эффективности",
    ]);
    expect(custom.name).toBe("Custom");
    expect(custom.price).toBe("—");
    expect(custom.period).toBe("по запросу");
    expect(custom.features).toEqual([
      "Безлимит источников",
      "Мониторинг в реальном времени",
      "Поддержка нескольких брендов",
      "Персональный онбординг",
    ]);
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
