"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
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

export function ContentPlanForm({ active }: { active: ActiveContext }) {
  const router = useRouter();
  const { locale, t } = useLanguage();

  const [options, setOptions] = useState<ContentPlanOptions>(EMPTY_OPTIONS);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsDebug, setOptionsDebug] = useState<ApiDebugInfo | null>(null);
  const [optionsFailed, setOptionsFailed] = useState(false);

  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [offer, setOffer] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [contentTypes, setContentTypes] = useState<string[]>([]);
  const [cta, setCta] = useState("");
  const [custom, setCustom] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitDebug, setSubmitDebug] = useState<ApiDebugInfo | null>(null);
  const [createdPath, setCreatedPath] = useState<string | null>(null);

  const loadOptions = useCallback(async () => {
    setLoadingOptions(true);
    setOptionsFailed(false);
    setOptionsDebug(null);
    try {
      const response = await apiRequest<Partial<ContentPlanOptions>>(
        `/reports/${active.report_id}/content-plan-options`,
        { method: "POST", body: JSON.stringify({ language: locale }) },
      );
      setOptions({ ...EMPTY_OPTIONS, ...response });
    } catch (value) {
      setOptionsFailed(true);
      setOptionsDebug(apiErrorDebugInfo(value));
    } finally {
      setLoadingOptions(false);
    }
  }, [active.report_id, locale]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  function toggle(list: string[], value: string): string[] {
    return list.includes(value)
      ? list.filter((item) => item !== value)
      : [...list, value];
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
        { goal, audience, offer, channels, contentTypes, cta, customInstruction: custom },
        locale,
      );
      const response = await apiRequest<{
        plan_id?: number | string | null;
        content_plan_id?: number | string | null;
      }>("/content-plans", { method: "POST", body: JSON.stringify(body) });
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
    return <LoadingState label={t("Готовим варианты по отчёту")} />;
  }
  if (optionsFailed) {
    return <FriendlyError debug={optionsDebug} onRetry={loadOptions} />;
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

  return (
    <form className="plan-builder" onSubmit={submit}>
      <SingleChipField
        label={t("Цель")}
        options={options.goals}
        value={goal}
        onChange={setGoal}
      />
      <SingleChipField
        label={t("Аудитория")}
        options={options.audiences}
        value={audience}
        onChange={setAudience}
      />
      <SingleChipField
        label={t("Оффер")}
        options={options.offers}
        value={offer}
        onChange={setOffer}
      />
      <MultiChipField
        label={t("Каналы")}
        options={options.channels}
        values={channels}
        onToggle={(value) => setChannels((list) => toggle(list, value))}
      />
      <MultiChipField
        label={t("Форматы")}
        options={options.content_types}
        values={contentTypes}
        onToggle={(value) => setContentTypes((list) => toggle(list, value))}
      />
      <SingleChipField
        label={t("Призыв к действию")}
        options={options.ctas}
        value={cta}
        onChange={setCta}
      />
      <label className="plan-builder-custom">
        <span>{t("Дополнительные пожелания")}</span>
        <textarea
          onChange={(event) => setCustom(event.target.value)}
          placeholder={t("Например: спокойный тон, без громких обещаний")}
          value={custom}
        />
      </label>

      {submitError ? (
        <FriendlyError
          debug={submitDebug}
          message={`${t("Не удалось создать контент-план.")} ${submitError}`}
        />
      ) : null}

      <div className="form-actions">
        <button className="button button-primary" disabled={submitting}>
          <Icon name={submitting ? "sync" : "book"} />
          {submitting ? t("Формируем план") : t("Создать контент-план")}
        </button>
      </div>
    </form>
  );
}

function SingleChipField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ContentPlanOption[];
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useLanguage();
  return (
    <fieldset className="plan-field">
      <legend>{label}</legend>
      {options.length ? (
        <div className="chip-row">
          {options.map((option) => (
            <button
              className={`chip${value === option.value ? " chip-active" : ""}`}
              key={`${option.label}-${option.value}`}
              onClick={() => onChange(value === option.value ? "" : option.value)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
      <input
        className="chip-input"
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("Или впишите своё")}
        value={value}
      />
    </fieldset>
  );
}

function MultiChipField({
  label,
  options,
  values,
  onToggle,
}: {
  label: string;
  options: ContentPlanOption[];
  values: string[];
  onToggle: (value: string) => void;
}) {
  if (!options.length) return null;
  return (
    <fieldset className="plan-field">
      <legend>{label}</legend>
      <div className="chip-row">
        {options.map((option) => (
          <button
            className={`chip${values.includes(option.value) ? " chip-active" : ""}`}
            key={`${option.label}-${option.value}`}
            onClick={() => onToggle(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
