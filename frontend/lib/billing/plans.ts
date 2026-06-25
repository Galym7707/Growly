export type BillingPlanId = "free" | "starter" | "pro" | "agency";
export type PaidBillingPlanId = Exclude<BillingPlanId, "free">;

export type BillingFeature =
  | "workspace:create"
  | "reports:more"
  | "publishing:auto"
  | "team:invite"
  | "workspaces:agency";

export type BillingPlan = {
  id: BillingPlanId;
  name: string;
  price: string;
  period: string;
  shortBenefit: string;
  cta: string;
  productEnvKey?: string;
  workspaceLimit: number;
  features: string[];
};

export const billingPlans: BillingPlan[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    shortBenefit: "Start with a simple marketing workspace.",
    cta: "Create account",
    workspaceLimit: 1,
    features: [
      "1 business/workspace",
      "Limited reports",
      "Limited content plan",
      "No autopublishing",
      "Team sharing limited",
    ],
  },
  {
    id: "starter",
    name: "Starter",
    price: "$19",
    period: "per month",
    shortBenefit: "Plan and prepare content for one business.",
    cta: "Start with Starter",
    productEnvKey: "POLAR_STARTER_PRODUCT_ID",
    workspaceLimit: 1,
    features: [
      "1 business/workspace",
      "Market reports",
      "Content plan",
      "Drafts",
      "Manual publishing package",
      "Basic team sharing",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$49",
    period: "per month",
    shortBenefit: "Run content planning across several workspaces.",
    cta: "Choose Pro",
    productEnvKey: "POLAR_PRO_PRODUCT_ID",
    workspaceLimit: 3,
    features: [
      "3 businesses/workspaces",
      "More reports",
      "Content calendar",
      "AI drafts",
      "Integrations",
      "Team sharing",
      "Scheduled publishing when available",
    ],
  },
  {
    id: "agency",
    name: "Agency",
    price: "$99",
    period: "per month",
    shortBenefit: "Manage client workspaces with your team.",
    cta: "Choose Agency",
    productEnvKey: "POLAR_AGENCY_PRODUCT_ID",
    workspaceLimit: 10,
    features: [
      "10 businesses/workspaces",
      "Client workspaces",
      "Team members",
      "Advanced publishing",
      "Priority support",
    ],
  },
];

export const paidBillingPlanIds: PaidBillingPlanId[] = [
  "starter",
  "pro",
  "agency",
];

const planRank: Record<BillingPlanId, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

const featureMinimumPlan: Record<BillingFeature, BillingPlanId> = {
  "workspace:create": "pro",
  "reports:more": "starter",
  "publishing:auto": "pro",
  "team:invite": "starter",
  "workspaces:agency": "agency",
};

export function normalizePlan(value: string | null | undefined): BillingPlanId {
  return value === "starter" || value === "pro" || value === "agency"
    ? value
    : "free";
}

export function getBillingPlan(plan: BillingPlanId): BillingPlan {
  return billingPlans.find((item) => item.id === plan) || billingPlans[0];
}

export function isPaidBillingPlan(plan: BillingPlanId): plan is PaidBillingPlanId {
  return plan !== "free";
}

export function planMeetsMinimum(
  currentPlan: BillingPlanId,
  minimumPlan: BillingPlanId,
): boolean {
  return planRank[currentPlan] >= planRank[minimumPlan];
}

export function canPlanUseFeature(
  currentPlan: BillingPlanId,
  feature: BillingFeature,
): boolean {
  return planMeetsMinimum(currentPlan, featureMinimumPlan[feature]);
}

export function requiredPlanForFeature(feature: BillingFeature): BillingPlan {
  return getBillingPlan(featureMinimumPlan[feature]);
}
