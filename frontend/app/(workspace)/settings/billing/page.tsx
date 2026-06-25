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
  getBillingPlan,
  type BillingPlanId,
  type PaidBillingPlanId,
} from "@/lib/billing/plans";
import { useLanguage } from "@/lib/i18n";

type BillingStatusResponse = {
  plan: BillingPlanId;
  status: string;
  nextBillingDate: string | null;
  cancelAtPeriodEnd: boolean;
  customerId: string | null;
  subscriptionId: string | null;
  configuredPlans: Record<"starter" | "pro" | "agency", boolean>;
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
  const { t, locale } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/billing/status", {
        credentials: "include",
        cache: "no-store",
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Could not load billing.");
      setBilling(body);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Could not load billing.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const currentPlan = useMemo(
    () => getBillingPlan(billing?.plan || "free"),
    [billing?.plan],
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
      if (!response.ok || !body.url) {
        throw new Error(body.detail || "Billing portal is not configured yet.");
      }
      window.location.assign(body.url);
    } catch (value) {
      setPortalError(
        value instanceof Error
          ? value.message
          : "Billing portal is not configured yet.",
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
      if (!response.ok || !body.url) {
        throw new Error(body.detail || "Payment is not configured yet.");
      }
      window.location.assign(body.url);
    } catch (value) {
      setCheckoutError(
        value instanceof Error ? value.message : "Payment is not configured yet.",
      );
    } finally {
      setCheckoutLoading(null);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Billing")}
        title={t("Subscription and billing")}
        description={t(
          "Manage your Growly plan, subscription status and billing portal access.",
        )}
        action={
          <Link className="button button-secondary" href="/#pricing">
            <Icon name="layers" />
            {t("View plans")}
          </Link>
        }
      />

      {loading ? <LoadingState /> : null}
      {error && loading ? <ErrorState message={error} retry={load} /> : null}

      {!loading && billing ? (
        <>
          <section className="billing-summary">
            <div>
              <p className="eyebrow">{t("Current plan")}</p>
              <h2>{currentPlan.name}</h2>
              <p>{currentPlan.shortBenefit}</p>
            </div>
            <div className="billing-summary-meta">
              <div>
                <span>{t("Status")}</span>
                <Status value={billing.status}>{billing.status}</Status>
              </div>
              <div>
                <span>{t("Next billing date")}</span>
                <strong>
                  {billing.nextBillingDate
                    ? new Intl.DateTimeFormat(locale, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      }).format(new Date(billing.nextBillingDate))
                    : t("No billing date")}
                </strong>
              </div>
              <div>
                <span>{t("Cancel at period end")}</span>
                <strong>{billing.cancelAtPeriodEnd ? t("Yes") : t("No")}</strong>
              </div>
            </div>
            <div className="billing-actions">
              <Link className="button button-primary" href="/#pricing">
                <Icon name="arrow" />
                {billing.plan === "free" ? t("Choose plan") : t("Upgrade")}
              </Link>
              <button
                className="button button-secondary"
                disabled={portalLoading}
                onClick={openPortal}
                type="button"
              >
                <Icon name="external" />
                {portalLoading ? t("Opening") : t("Manage billing")}
              </button>
            </div>
            {portalError ? (
              <div className="feedback feedback-warning">{portalError}</div>
            ) : null}
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{t("Plans")}</p>
                <h2>{t("Choose the workspace size")}</h2>
              </div>
            </div>
            <div className="billing-plan-grid">
              {billingPlans.map((plan) => {
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
                      <h3>{plan.name}</h3>
                      <p>{plan.shortBenefit}</p>
                    </div>
                    <div className="billing-plan-price">
                      <strong>{plan.price}</strong>
                      <span>{plan.period}</span>
                    </div>
                    <ul>
                      {plan.features.map((feature) => (
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
                        {checkoutLoading === paidPlanId ? t("Opening") : plan.cta}
                      </button>
                    ) : (
                      <button className="button button-secondary" disabled type="button">
                        Payment is not configured yet.
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
