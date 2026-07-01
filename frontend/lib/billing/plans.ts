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
  unavailableFeatures?: string[];
};

export type BillingPlanLocale = "ru" | "en" | "kk";

export type BillingPlanDisplay = {
  name: string;
  price: string;
  period: string;
  shortBenefit: string;
  cta: string;
  features: string[];
  unavailableFeatures?: string[];
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
    shortBenefit: "A compact plan for the first competitor signals and weekly content planning.",
    cta: "Buy plan",
    productEnvKey: "POLAR_STARTER_PRODUCT_ID",
    workspaceLimit: 1,
    features: [
      "5 competitor sources",
      "Weekly content plan",
      "8 drafts/month",
    ],
    unavailableFeatures: ["CRM integration"],
  },
  {
    id: "pro",
    name: "Growth",
    price: "$49",
    period: "per month",
    shortBenefit: "More sources, unlimited drafts, CRM cases, and weekly performance reporting.",
    cta: "Buy plan",
    productEnvKey: "POLAR_PRO_PRODUCT_ID",
    workspaceLimit: 3,
    features: [
      "25 competitor sources",
      "Unlimited drafts",
      "CRM case builder",
      "Weekly performance reports",
    ],
  },
  {
    id: "agency",
    name: "Custom",
    price: "—",
    period: "talk to us",
    shortBenefit: "A custom setup for unlimited sources, real-time monitoring, and several brands.",
    cta: "Talk to us",
    productEnvKey: "POLAR_AGENCY_PRODUCT_ID",
    workspaceLimit: 10,
    features: [
      "Unlimited sources",
      "Real-time monitoring",
      "Multi-brand support",
      "Dedicated onboarding",
    ],
  },
];

const billingPlanDisplay: Record<
  BillingPlanId,
  Record<BillingPlanLocale, BillingPlanDisplay>
> = {
  free: {
    ru: {
      name: "Бесплатный",
      price: "$0",
      period: "навсегда",
      shortBenefit: "Стартовый кабинет для проверки идеи и первых материалов.",
      cta: "Создать аккаунт",
      features: [
        "1 бизнес / рабочая область",
        "Ограниченное число отчётов",
        "Ограниченный контент-план",
        "Без автопубликации",
        "Базовое совместное использование",
      ],
    },
    en: {
      name: "Free",
      price: "$0",
      period: "forever",
      shortBenefit: "A starter workspace for validating an idea and first assets.",
      cta: "Create account",
      features: [
        "1 business / workspace",
        "Limited reports",
        "Limited content plan",
        "No autopublishing",
        "Basic sharing",
      ],
    },
    kk: {
      name: "Тегін",
      price: "$0",
      period: "мәңгі",
      shortBenefit: "Идеяны және алғашқы материалдарды тексеруге арналған бастапқы кабинет.",
      cta: "Аккаунт жасау",
      features: [
        "1 бизнес / жұмыс кеңістігі",
        "Шектеулі есептер",
        "Шектеулі контент-жоспар",
        "Автожариялау жоқ",
        "Базалық бөлісу",
      ],
    },
  },
  starter: {
    ru: {
      name: "Starter",
      price: "$19",
      period: "в месяц",
      shortBenefit: "Компактный тариф для первых сигналов конкурентов и еженедельного контент-плана.",
      cta: "Купить тариф",
      features: [
        "5 источников конкурентов",
        "Еженедельный контент-план",
        "8 черновиков в месяц",
      ],
      unavailableFeatures: ["Интеграция с CRM"],
    },
    en: {
      name: "Starter",
      price: "$19",
      period: "per month",
      shortBenefit: "A compact plan for the first competitor signals and weekly content planning.",
      cta: "Buy plan",
      features: [
        "5 competitor sources",
        "Weekly content plan",
        "8 drafts / month",
      ],
      unavailableFeatures: ["CRM integration"],
    },
    kk: {
      name: "Starter",
      price: "$19",
      period: "айына",
      shortBenefit: "Алғашқы бәсекелес сигналдары мен апталық контент-жоспарға арналған ықшам тариф.",
      cta: "Тарифті сатып алу",
      features: [
        "5 бәсекелес дереккөзі",
        "Апталық контент-жоспар",
        "Айына 8 жоба",
      ],
      unavailableFeatures: ["CRM интеграциясы"],
    },
  },
  pro: {
    ru: {
      name: "Growth",
      price: "$49",
      period: "в месяц",
      shortBenefit: "Больше источников, безлимит черновиков, CRM-кейсы и еженедельные отчёты.",
      cta: "Купить тариф",
      features: [
        "25 источников конкурентов",
        "Безлимит черновиков",
        "Кейс-машина для CRM",
        "Еженедельные отчёты по эффективности",
      ],
    },
    en: {
      name: "Growth",
      price: "$49",
      period: "per month",
      shortBenefit: "More sources, unlimited drafts, CRM cases, and weekly performance reporting.",
      cta: "Buy plan",
      features: [
        "25 competitor sources",
        "Unlimited drafts",
        "CRM case builder",
        "Weekly performance reports",
      ],
    },
    kk: {
      name: "Growth",
      price: "$49",
      period: "айына",
      shortBenefit: "Көбірек дереккөз, шексіз жобалар, CRM кейстері және апталық тиімділік есептері.",
      cta: "Тарифті сатып алу",
      features: [
        "25 бәсекелес дереккөзі",
        "Шексіз жобалар",
        "CRM үшін кейс-машина",
        "Апталық тиімділік есептері",
      ],
    },
  },
  agency: {
    ru: {
      name: "Custom",
      price: "—",
      period: "по запросу",
      shortBenefit: "Индивидуальная настройка для безлимитных источников, real-time мониторинга и нескольких брендов.",
      cta: "Связаться с нами",
      features: [
        "Безлимит источников",
        "Мониторинг в реальном времени",
        "Поддержка нескольких брендов",
        "Персональный онбординг",
      ],
    },
    en: {
      name: "Custom",
      price: "—",
      period: "talk to us",
      shortBenefit: "A custom setup for unlimited sources, real-time monitoring, and several brands.",
      cta: "Talk to us",
      features: [
        "Unlimited sources",
        "Real-time monitoring",
        "Multi-brand support",
        "Dedicated onboarding",
      ],
    },
    kk: {
      name: "Custom",
      price: "—",
      period: "сұраныс бойынша",
      shortBenefit: "Шексіз дереккөздерге, нақты уақыттағы бақылауға және бірнеше брендке арналған жеке баптау.",
      cta: "Бізбен байланысу",
      features: [
        "Шексіз дереккөздер",
        "Нақты уақыттағы бақылау",
        "Бірнеше брендке қолдау",
        "Жеке енгізу қолдауы",
      ],
    },
  },
};

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

export function getBillingPlanDisplay(
  plan: BillingPlanId,
  locale: BillingPlanLocale,
): BillingPlanDisplay {
  return billingPlanDisplay[plan][locale] || billingPlanDisplay[plan].ru;
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
