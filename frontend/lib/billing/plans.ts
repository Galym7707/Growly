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

export type BillingPlanLocale = "ru" | "en" | "kk";

export type BillingPlanDisplay = {
  name: string;
  price: string;
  period: string;
  shortBenefit: string;
  cta: string;
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
      shortBenefit: "Планирование и подготовка контента для одного бизнеса.",
      cta: "Начать со Starter",
      features: [
        "1 бизнес / рабочая область",
        "Рыночные отчёты",
        "Контент-план",
        "Черновики",
        "Пакет для ручной публикации",
        "Базовая работа с командой",
      ],
    },
    en: {
      name: "Starter",
      price: "$19",
      period: "per month",
      shortBenefit: "Plan and prepare content for one business.",
      cta: "Start with Starter",
      features: [
        "1 business / workspace",
        "Market reports",
        "Content plan",
        "Drafts",
        "Manual publishing package",
        "Basic team sharing",
      ],
    },
    kk: {
      name: "Starter",
      price: "$19",
      period: "айына",
      shortBenefit: "Бір бизнеске контентті жоспарлау және дайындау.",
      cta: "Starter-мен бастау",
      features: [
        "1 бизнес / жұмыс кеңістігі",
        "Нарық есептері",
        "Контент-жоспар",
        "Нобайлар",
        "Қолмен жариялау пакеті",
        "Командамен базалық жұмыс",
      ],
    },
  },
  pro: {
    ru: {
      name: "Pro",
      price: "$49",
      period: "в месяц",
      shortBenefit: "Контент-процесс для нескольких рабочих областей.",
      cta: "Выбрать Pro",
      features: [
        "3 бизнеса / рабочие области",
        "Больше отчётов",
        "Контент-календарь",
        "AI-черновики",
        "Интеграции",
        "Командная работа",
        "Запланированная публикация при доступности",
      ],
    },
    en: {
      name: "Pro",
      price: "$49",
      period: "per month",
      shortBenefit: "Run content planning across several workspaces.",
      cta: "Choose Pro",
      features: [
        "3 businesses / workspaces",
        "More reports",
        "Content calendar",
        "AI drafts",
        "Integrations",
        "Team sharing",
        "Scheduled publishing when available",
      ],
    },
    kk: {
      name: "Pro",
      price: "$49",
      period: "айына",
      shortBenefit: "Бірнеше жұмыс кеңістігіне арналған контент-процесс.",
      cta: "Pro таңдау",
      features: [
        "3 бизнес / жұмыс кеңістігі",
        "Көбірек есептер",
        "Контент-күнтізбе",
        "AI нобайлар",
        "Интеграциялар",
        "Командалық жұмыс",
        "Қолжетімді болса жоспарланған жариялау",
      ],
    },
  },
  agency: {
    ru: {
      name: "Agency",
      price: "$99",
      period: "в месяц",
      shortBenefit: "Управление клиентскими рабочими областями с командой.",
      cta: "Выбрать Agency",
      features: [
        "10 бизнесов / рабочих областей",
        "Клиентские рабочие области",
        "Участники команды",
        "Расширенная публикация",
        "Приоритетная поддержка",
      ],
    },
    en: {
      name: "Agency",
      price: "$99",
      period: "per month",
      shortBenefit: "Manage client workspaces with your team.",
      cta: "Choose Agency",
      features: [
        "10 businesses / workspaces",
        "Client workspaces",
        "Team members",
        "Advanced publishing",
        "Priority support",
      ],
    },
    kk: {
      name: "Agency",
      price: "$99",
      period: "айына",
      shortBenefit: "Командамен клиент жұмыс кеңістіктерін басқару.",
      cta: "Agency таңдау",
      features: [
        "10 бизнес / жұмыс кеңістігі",
        "Клиент жұмыс кеңістіктері",
        "Команда қатысушылары",
        "Кеңейтілген жариялау",
        "Басым қолдау",
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
