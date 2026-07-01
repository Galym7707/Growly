"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  Status,
} from "@/components/ui";
import {
  billingPlans,
  getBillingPlanDisplay,
  type BillingPlanId,
  type PaidBillingPlanId,
} from "@/lib/billing/plans";
import type { CreditPack, CreditPackId } from "@/lib/billing/credits";
import { apiRequest } from "@/lib/api";
import { useLanguage, type Locale } from "@/lib/i18n";

type ConfiguredCreditPack = CreditPack & { configured: boolean };

type BillingStatusResponse = {
  plan: BillingPlanId;
  status: string;
  nextBillingDate: string | null;
  cancelAtPeriodEnd: boolean;
  customerId: string | null;
  subscriptionId: string | null;
  configuredPlans: Record<"starter" | "pro" | "agency", boolean>;
  creditPacks?: ConfiguredCreditPack[];
};

export default function BillingSettingsPage() {
  const [billing, setBilling] = useState<BillingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutLoading, setCheckoutLoading] =
    useState<PaidBillingPlanId | null>(null);
  const [portalError, setPortalError] = useState("");
  const [portalLoading, setPortalLoading] = useState(false);
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const [creditsCheckoutError, setCreditsCheckoutError] = useState("");
  const [creditsCheckoutLoading, setCreditsCheckoutLoading] =
    useState<CreditPackId | null>(null);
  const { t, locale } = useLanguage();

  const loadCreditBalance = useCallback(async () => {
    try {
      const info = await apiRequest<{ balance: number }>(
        "/integrations/video/credits",
      );
      setCreditBalance(info.balance);
    } catch {
      setCreditBalance(null);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/billing/status", {
        credentials: "include",
        cache: "no-store",
      });
      const body = await response.json();
      if (!response.ok) throw new Error(t("Не удалось загрузить данные по оплате."));
      setBilling(body);
      void loadCreditBalance();
    } catch (value) {
      setError(
        value instanceof Error
          ? value.message
          : t("Не удалось загрузить данные по оплате."),
      );
    } finally {
      setLoading(false);
    }
  }, [t, loadCreditBalance]);

  useEffect(() => {
    void load();
  }, [load]);

  const currentPlanDisplay = useMemo(
    () => getBillingPlanDisplay(billing?.plan || "free", locale),
    [billing?.plan, locale],
  );

  async function openPortal() {
    setPortalLoading(true);
    setPortalError("");
    try {
      const response = await fetch("/api/billing/portal", {
        method: "POST",
        credentials: "include",
      });
      const body = await response.json();
      if (!response.ok || !body.url) throw new Error();
      window.location.assign(body.url);
    } catch (value) {
      setPortalError(
        value instanceof Error
          ? value.message || t("Платёжный кабинет пока не настроен.")
          : t("Платёжный кабинет пока не настроен."),
      );
    } finally {
      setPortalLoading(false);
    }
  }

  async function startCheckout(plan: PaidBillingPlanId) {
    setCheckoutLoading(plan);
    setCheckoutError("");
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const body = await response.json();
      if (!response.ok || !body.url) throw new Error();
      window.location.assign(body.url);
    } catch (value) {
      setCheckoutError(
        value instanceof Error
          ? value.message || t("Оплата пока не настроена.")
          : t("Оплата пока не настроена."),
      );
    } finally {
      setCheckoutLoading(null);
    }
  }

  async function buyCredits(pack: CreditPackId) {
    setCreditsCheckoutLoading(pack);
    setCreditsCheckoutError("");
    try {
      const response = await fetch("/api/billing/credits/checkout", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack }),
      });
      const body = await response.json();
      if (!response.ok || !body.url) throw new Error();
      window.location.assign(body.url);
    } catch (value) {
      setCreditsCheckoutError(
        value instanceof Error
          ? value.message || t("Оплата пока не настроена.")
          : t("Оплата пока не настроена."),
      );
    } finally {
      setCreditsCheckoutLoading(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Оплата")}
        title={t("Тариф и оплата")}
        description={t(
          "Управляйте тарифом Growly, статусом подписки и доступом к платёжному кабинету.",
        )}
        action={
          <Link className="button button-secondary" href="/#pricing">
            <Icon name="layers" />
            {t("Посмотреть тарифы")}
          </Link>
        }
      />

      {loading ? <LoadingState /> : null}
      {error && loading ? <ErrorState message={error} retry={load} /> : null}

      {!loading && billing ? (
        <>
          <section className="billing-summary">
            <div>
              <p className="eyebrow">{t("Текущий тариф")}</p>
              <h2>{currentPlanDisplay.name}</h2>
              <p>{currentPlanDisplay.shortBenefit}</p>
            </div>
            <div className="billing-summary-meta">
              <div>
                <span>{t("Статус")}</span>
                <Status value={billing.status}>
                  {billingStatusLabel(billing.status, locale)}
                </Status>
              </div>
              <div>
                <span>{t("Следующее списание")}</span>
                <strong>
                  {billing.nextBillingDate
                    ? new Intl.DateTimeFormat(locale, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      }).format(new Date(billing.nextBillingDate))
                    : t("Нет даты списания")}
                </strong>
              </div>
              <div>
                <span>{t("Отмена в конце периода")}</span>
                <strong>{billing.cancelAtPeriodEnd ? t("Да") : t("Нет")}</strong>
              </div>
            </div>
            <div className="billing-actions">
              <Link className="button button-primary" href="/#pricing">
                <Icon name="arrow" />
                {billing.plan === "free" ? t("Выбрать тариф") : t("Изменить тариф")}
              </Link>
              <button
                className="button button-secondary"
                disabled={portalLoading}
                onClick={openPortal}
                type="button"
              >
                <Icon name="external" />
                {portalLoading ? t("Открываем") : t("Управлять оплатой")}
              </button>
            </div>
            {portalError ? (
              <div className="feedback feedback-warning">{portalError}</div>
            ) : null}
          </section>

          <section className="workspace-section" id="credits">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Кредиты на видео")}</p>
                <h2>{t("Генерация ИИ-видео (Replicate)")}</h2>
                <p className="muted">
                  {t(
                    "Оплатите пакет кредитов, чтобы генерировать ИИ-видео через Replicate. 1 видео списывает 1 кредит.",
                  )}
                </p>
              </div>
              <div className="billing-summary-meta">
                <div>
                  <span>{t("Баланс кредитов")}</span>
                  <strong>{creditBalance ?? 0}</strong>
                </div>
              </div>
            </div>
            <div className="billing-plan-grid">
              {(billing.creditPacks || []).map((pack) => (
                <article className="billing-plan-card" key={pack.id}>
                  <div>
                    <h3>
                      {pack.credits} {t("кредитов")}
                    </h3>
                    <p>
                      {pack.credits} {t("ИИ-видео для соцсетей")}
                    </p>
                  </div>
                  <div className="billing-plan-price">
                    <strong>{pack.price}</strong>
                    <span>{t("разовый платёж")}</span>
                  </div>
                  {pack.configured ? (
                    <button
                      className="button button-primary"
                      disabled={creditsCheckoutLoading === pack.id}
                      onClick={() => buyCredits(pack.id)}
                      type="button"
                    >
                      {creditsCheckoutLoading === pack.id
                        ? t("Открываем")
                        : t("Купить кредиты")}
                    </button>
                  ) : (
                    <button
                      className="button button-secondary"
                      disabled
                      type="button"
                    >
                      {t("Оплата пока не настроена.")}
                    </button>
                  )}
                </article>
              ))}
              {(billing.creditPacks || []).length === 0 ? (
                <p className="muted">
                  {t("Пакеты кредитов пока не настроены.")}
                </p>
              ) : null}
            </div>
            {creditsCheckoutError ? (
              <div className="feedback feedback-warning">
                {creditsCheckoutError}
              </div>
            ) : null}
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Тарифы")}</p>
                <h2>{t("Выберите размер рабочей области")}</h2>
              </div>
            </div>
            <div className="billing-plan-grid">
              {billingPlans.map((plan) => {
                const planDisplay = getBillingPlanDisplay(plan.id, locale);
                const paidPlanId =
                  plan.id === "free" ? null : (plan.id as PaidBillingPlanId);
                const configured = paidPlanId
                  ? billing.configuredPlans[paidPlanId]
                  : true;
                return (
                  <article
                    className={`billing-plan-card ${
                      plan.id === billing.plan ? "active" : ""
                    }`}
                    key={plan.id}
                  >
                    <div>
                      <h3>{planDisplay.name}</h3>
                      <p>{planDisplay.shortBenefit}</p>
                    </div>
                    <div className="billing-plan-price">
                      <strong>{planDisplay.price}</strong>
                      <span>{planDisplay.period}</span>
                    </div>
                    <ul>
                      {planDisplay.features.map((feature) => (
                        <li key={feature}>
                          <Icon name="check" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    {plan.id === "free" ? (
                      <Link className="button button-secondary" href="/register">
                        {t("Create account")}
                      </Link>
                    ) : configured ? (
                      <button
                        className="button button-primary"
                        disabled={checkoutLoading === paidPlanId}
                        onClick={() => paidPlanId && startCheckout(paidPlanId)}
                        type="button"
                      >
                        {checkoutLoading === paidPlanId
                          ? t("Открываем")
                          : planDisplay.cta}
                      </button>
                    ) : (
                      <button className="button button-secondary" disabled type="button">
                        {t("Оплата пока не настроена.")}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
            {checkoutError ? (
              <div className="feedback feedback-warning">{checkoutError}</div>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}

function billingStatusLabel(status: string, locale: Locale): string {
  const normalized = status.toLowerCase();
  const labels: Record<Locale, Record<string, string>> = {
    ru: {
      active: "Активна",
      trialing: "Пробный период",
      past_due: "Нужна оплата",
      unpaid: "Не оплачена",
      canceled: "Отменена",
      free: "Бесплатный тариф",
    },
    en: {
      active: "Active",
      trialing: "Trialing",
      past_due: "Past due",
      unpaid: "Unpaid",
      canceled: "Canceled",
      free: "Free plan",
    },
    kk: {
      active: "Белсенді",
      trialing: "Сынақ кезеңі",
      past_due: "Төлем қажет",
      unpaid: "Төленбеген",
      canceled: "Бас тартылған",
      free: "Тегін тариф",
    },
  };
  return labels[locale][normalized] || status;
}
