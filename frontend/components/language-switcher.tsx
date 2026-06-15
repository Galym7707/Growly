"use client";

import { useLanguage, type Locale } from "@/lib/i18n";

const options: Locale[] = ["ru", "en", "kk"];

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useLanguage();

  return (
    <div
      aria-label={t("Язык")}
      className={`language-switcher ${compact ? "language-switcher-compact" : ""}`}
      role="group"
    >
      {options.map((option) => (
        <button
          aria-pressed={locale === option}
          className={locale === option ? "active" : ""}
          key={option}
          onClick={() => setLocale(option)}
          type="button"
        >
          {option.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
