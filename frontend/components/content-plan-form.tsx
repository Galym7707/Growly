"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/icons";
import { FriendlyError } from "@/components/friendly-error";
import { LoadingState } from "@/components/ui";
import {
  apiErrorDebugInfo,
  apiRequest,
  type ApiDebugInfo,
} from "@/lib/api";
import {
  contentPlanSubmitBody,
  fallbackContentPlanOptions,
  type ActiveContext,
} from "@/lib/active-context";
import { contentPlanPathFromGeneratedResponse } from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";
import type { ContentPlanOption, ContentPlanOptions } from "@/lib/types";

const EMPTY_OPTIONS: ContentPlanOptions = {
  goals: [],
  audiences: [],
  offers: [],
  channels: [],
  content_types: [],
  ctas: [],
};

const CHANNEL_DEFAULTS: ContentPlanOption[] = [
  { label: "Telegram", value: "telegram" },
  { label: "Instagram", value: "instagram" },
  { label: "Threads", value: "threads" },
  { label: "WhatsApp", value: "whatsapp" },
  { label: "Сайт", value: "website" },
];

function ensureChannels(channels: ContentPlanOption[]): ContentPlanOption[] {
  const seen = new Set(channels.map((option) => option.value));
  const merged = [...channels];
  for (const fallback of CHANNEL_DEFAULTS) {
    if (!seen.has(fallback.value)) merged.push(fallback);
  }
  return merged;
}

function draftKey(reportId: number): string {
  return `growly_plan_draft_${reportId}`;
}

export function ContentPlanForm({ active }: { active: ActiveContext }) {
  const router = useRouter();
  const { locale, t } = useLanguage();

  const [options, setOptions] = useState<ContentPlanOptions>(EMPTY_OPTIONS);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [usedFallback, setUsedFallback] = useState(false);

  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [offer, setOffer] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [cta, setCta] = useState("");
  const [custom, setCustom] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitDebug, setSubmitDebug] = useState<ApiDebugInfo | null>(null);
  const [createdPath, setCreatedPath] = useState<string | null>(null);
  const [draftNote, setDraftNote] = useState("");

  const restored = useRef(false);

  const loadOptions = useCallback(async () => {
    setLoadingOptions(true);
    setUsedFallback(false);
    try {
      const response = await apiRequest<Partial<ContentPlanOptions>>(
        `/reports/${active.report_id}/content-plan-options`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      const merged = { ...EMPTY_OPTIONS, ...response };
      const hasAny = Object.values(merged).some(
        (list) => Array.isArray(list) && list.length > 0,
      );
      if (hasAny) {
        setOptions(merged);
      } else {
        setOptions(fallbackContentPlanOptions(active, locale));
        setUsedFallback(true);
      }
    } catch {
      setOptions(fallbackContentPlanOptions(active, locale));
      setUsedFallback(true);
    } finally {
      setLoadingOptions(false);
    }
  }, [active, locale]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  // Restore a locally saved draft for this report (once).
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(draftKey(active.report_id));
      if (!raw) return;
      const draft = JSON.parse(raw) as Record<string, unknown>;
      if (typeof draft.goal === "string") setGoal(draft.goal);
      if (typeof draft.audience === "string") setAudience(draft.audience);
      if (typeof draft.offer === "string") setOffer(draft.offer);
      if (Array.isArray(draft.channels)) setChannels(draft.channels as string[]);
      if (typeof draft.cta === "string") setCta(draft.cta);
      if (typeof draft.custom === "string") setCustom(draft.custom);
    } catch {
      // Ignore malformed drafts.
    }
  }, [active.report_id]);

  const channelOptions = ensureChannels(options.channels);
  const allChannelsSelected =
    channelOptions.length > 0 &&
    channelOptions.every((option) => channels.includes(option.value));

  function toggleChannel(value: string) {
    setChannels((list) =>
      list.includes(value)
        ? list.filter((item) => item !== value)
        : [...list, value],
    );
  }

  function toggleAllChannels() {
    setChannels(
      allChannelsSelected ? [] : channelOptions.map((option) => option.value),
    );
  }

  function saveDraft() {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        draftKey(active.report_id),
        JSON.stringify({ goal, audience, offer, channels, cta, custom }),
      );
      setDraftNote(t("Черновик сохранён."));
      window.setTimeout(() => setDraftNote(""), 2500);
    } catch {
      // Ignore storage failures.
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError("");
    setSubmitDebug(null);
    setCreatedPath(null);
    try {
      const body = contentPlanSubmitBody(
        active.report_id,
        { goal, audience, offer, channels, contentTypes: [], cta, customInstruction: custom },
        locale,
      );
      const response = await apiRequest<{
        plan_id?: number | string | null;
        content_plan_id?: number | string | null;
      }>("/content-plans", { method: "POST", body: JSON.stringify(body) });
      if (typeof window !== "undefined") {
        try {
          window.localStorage.removeItem(draftKey(active.report_id));
        } catch {
          // Ignore.
        }
      }
      const path = contentPlanPathFromGeneratedResponse(response);
      if (path) {
        router.push(path);
      } else {
        setCreatedPath("/content-plan");
      }
    } catch (value) {
      setSubmitDebug(apiErrorDebugInfo(value));
      setSubmitError(
        value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingOptions) {
    return <LoadingState label={t("Готовлю варианты для контент-плана…")} />;
  }

  if (createdPath) {
    return (
      <div className="feedback feedback-success">
        {t("Контент-план создан.")}
        <div className="feedback-actions">
          <button
            className="button button-secondary button-small"
            onClick={() => router.push(createdPath)}
            type="button"
          >
            {t("Открыть контент-план")}
          </button>
        </div>
      </div>
    );
  }

  const steps = [
    { label: t("Цель"), done: Boolean(goal.trim()), href: "#step-goal" },
    { label: t("Аудитория"), done: Boolean(audience.trim()), href: "#step-audience" },
    { label: t("Оффер"), done: Boolean(offer.trim()), href: "#step-offer" },
    { label: t("Каналы"), done: channels.length > 0, href: "#step-channels" },
    { label: t("Призыв к действию"), done: Boolean(cta.trim()), href: "#step-cta" },
    { label: t("Создание"), done: false, href: "#step-create" },
  ];

  return (
    <form className="plan-wizard" onSubmit={submit}>
      <ol className="wizard-steps">
        {steps.map((step, index) => (
          <li key={step.label}>
            <a className={`wizard-step${step.done ? " wizard-step-done" : ""}`} href={step.href}>
              <span className="wizard-step-index">
                {step.done ? <Icon name="check" /> : index + 1}
              </span>
              <span>{step.label}</span>
            </a>
          </li>
        ))}
      </ol>

      <p className={`plan-note${usedFallback ? "" : " plan-note-muted"}`}>
        {usedFallback
          ? t("Показали базовые варианты. Можно обновить или вписать свой вариант.")
          : t("Варианты подготовлены на основе выбранного отчёта.")}
        {usedFallback ? (
          <button className="text-link" onClick={loadOptions} type="button">
            {t("Обновить варианты")}
          </button>
        ) : null}
      </p>

      <WizardCard
        anchor="step-goal"
        step={1}
        title={t("Что должен сделать контент на этой неделе?")}
      >
        <SingleChipField options={options.goals} value={goal} onChange={setGoal} />
      </WizardCard>

      <WizardCard
        anchor="step-audience"
        step={2}
        title={t("Для кого создаём контент?")}
      >
        <SingleChipField
          options={options.audiences}
          value={audience}
          onChange={setAudience}
        />
      </WizardCard>

      <WizardCard anchor="step-offer" step={3} title={t("Что продвигаем?")}>
        <SingleChipField options={options.offers} value={offer} onChange={setOffer} />
      </WizardCard>

      <WizardCard anchor="step-channels" step={4} title={t("Где публикуем?")}>
        <div className="chip-row">
          {channelOptions.map((option) => (
            <Chip
              key={option.value}
              label={option.label}
              selected={channels.includes(option.value)}
              onClick={() => toggleChannel(option.value)}
            />
          ))}
          <Chip
            label={t("Все каналы")}
            selected={allChannelsSelected}
            onClick={toggleAllChannels}
          />
        </div>
      </WizardCard>

      <WizardCard
        anchor="step-cta"
        step={5}
        title={t("Какое действие должен совершить клиент?")}
      >
        <SingleChipField options={options.ctas} value={cta} onChange={setCta} />
      </WizardCard>

      <WizardCard
        anchor="step-create"
        step={6}
        title={t("Дополнительная инструкция (необязательно)")}
      >
        <textarea
          className="wizard-textarea"
          onChange={(event) => setCustom(event.target.value)}
          placeholder={t("Например: спокойный тон, без громких обещаний")}
          value={custom}
        />
      </WizardCard>

      {submitError ? (
        <FriendlyError
          debug={submitDebug}
          message={`${t("Не удалось создать контент-план.")} ${submitError}`}
        />
      ) : null}

      <div className="wizard-actions">
        {draftNote ? <span className="wizard-draft-note">{draftNote}</span> : null}
        <button
          className="button button-secondary"
          onClick={saveDraft}
          type="button"
        >
          {t("Сохранить как черновик")}
        </button>
        <button className="button button-primary" disabled={submitting}>
          <Icon name={submitting ? "sync" : "book"} />
          {submitting ? t("Формируем план") : t("Создать контент-план")}
        </button>
      </div>
    </form>
  );
}

function WizardCard({
  anchor,
  step,
  title,
  children,
}: {
  anchor: string;
  step: number;
  title: string;
  children: React.ReactNode;
}) {
  const { t } = useLanguage();
  return (
    <section className="wizard-card" id={anchor}>
      <p className="eyebrow">{t("Шаг {step}", { step })}</p>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Chip({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={selected}
      className={`chip${selected ? " chip-active" : ""}`}
      onClick={onClick}
      type="button"
    >
      {selected ? <Icon name="check" /> : null}
      {label}
    </button>
  );
}

function SingleChipField({
  options,
  value,
  onChange,
}: {
  options: ContentPlanOption[];
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useLanguage();
  return (
    <>
      {options.length ? (
        <div className="chip-row">
          {options.map((option) => (
            <Chip
              key={`${option.label}-${option.value}`}
              label={option.label}
              selected={value === option.value}
              onClick={() => onChange(value === option.value ? "" : option.value)}
            />
          ))}
        </div>
      ) : null}
      <input
        className="chip-input"
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("Свой вариант")}
        value={value}
      />
    </>
  );
}
