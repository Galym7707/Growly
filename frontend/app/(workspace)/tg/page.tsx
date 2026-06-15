"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { useLanguage } from "@/lib/i18n";

const links = [
  {
    href: "/market-scan",
    title: "Анализ рынка",
    text: "Запустить новый сбор источников.",
    icon: "market" as const,
  },
  {
    href: "/drafts",
    title: "Черновики",
    text: "Проверить материалы на согласовании.",
    icon: "draft" as const,
  },
  {
    href: "/reports",
    title: "Отчёты",
    text: "Открыть последние результаты.",
    icon: "report" as const,
  },
];

export default function TelegramEntryPage() {
  const { t } = useLanguage();

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Мобильный режим")}
        title={t("Growly для Telegram")}
        description={t("Компактная точка входа, подготовленная для будущего Telegram Mini App.")}
      />
      <div className="quick-action-list">
        {links.map((item) => (
          <Link href={item.href} key={item.href}>
            <Icon name={item.icon} />
            <div>
              <strong>{t(item.title)}</strong>
              <span>{t(item.text)}</span>
            </div>
            <Icon name="arrow" />
          </Link>
        ))}
      </div>
      <section className="workspace-section">
        <div className="form-panel">
          <h2>{t("Проверка Telegram-пользователя")}</h2>
          <p>
            {t("Эта страница пока использует обычную веб-сессию. При подключении Mini App параметр initData должен проверяться на сервере; данные из initDataUnsafe не используются как доверенный источник.")}
          </p>
        </div>
      </section>
    </div>
  );
}
