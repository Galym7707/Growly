"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Report } from "@/lib/types";

const steps = [
  "Ищу источники",
  "Сохраняю данные",
  "Анализирую",
  "Формирую отчёт",
  "Синхронизирую с Notion",
];

export default function MarketScanPage() {
  const [niche, setNiche] = useState("");
  const [region, setRegion] = useState("Казахстан, русский язык");
  const [competitors, setCompetitors] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Report | null>(null);
  const { locale, t } = useLanguage();

  useEffect(() => {
    setRegion(
      locale === "en"
        ? "Kazakhstan, English"
        : locale === "kk"
          ? "Қазақстан, қазақ тілі"
          : "Казахстан, русский язык",
    );
  }, [locale]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await apiRequest<{
        report: Report;
        sources_saved: number;
      }>("/market-scan", {
        method: "POST",
        body: JSON.stringify({
          niche,
          region_language: region,
          competitor_keywords: competitors,
        }),
      });
      setResult(response.report);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Исследование")}
        title={t("Анализ рынка")}
        description={t("Growly сначала сохраняет публичные источники, затем формирует выводы и отчёт.")}
      />
      <form className="form-panel" onSubmit={submit}>
        <h2>{t("Параметры анализа")}</h2>
        <p>
          {t("Опишите рынок достаточно конкретно, чтобы поиск не смешивал разные категории.")}
        </p>
        <div className="form-grid">
          <label className="full">
            <span>{t("Ниша или продукт")}</span>
            <input
              onChange={(event) => setNiche(event.target.value)}
              placeholder={t("Например: доставка здорового питания для офисов")}
              required
              value={niche}
            />
          </label>
          <label>
            <span>{t("Регион и язык")}</span>
            <input
              onChange={(event) => setRegion(event.target.value)}
              required
              value={region}
            />
          </label>
          <label>
            <span>{t("Известные конкуренты")}</span>
            <input
              onChange={(event) => setCompetitors(event.target.value)}
              placeholder={t("Можно оставить пустым")}
              value={competitors}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="button button-primary" disabled={loading}>
            <Icon name={loading ? "sync" : "search"} />
            {t(loading ? "Анализ выполняется" : "Запустить анализ")}
          </button>
        </div>
      </form>
      {loading ? (
        <div className="task-progress" aria-live="polite">
          {steps.map((step, index) => (
            <div className={index === 0 ? "active" : ""} key={step}>
              <Icon name={index === 0 ? "sync" : "chevron"} />
              {t(step)}
            </div>
          ))}
        </div>
      ) : null}
      {error ? <div className="feedback feedback-error">{error}</div> : null}
      {result ? (
        <div className="feedback feedback-success">
          {t("Отчёт готов. Сохранено источников: {count}.", {
            count: result.sources_count,
          })}{" "}
          <Link href={`/reports/${result.id}`}>{t("Открыть отчёт")}</Link>
        </div>
      ) : null}
    </div>
  );
}
