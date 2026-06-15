import Link from "next/link";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";

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
  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Мобильный режим"
        title="Growly для Telegram"
        description="Компактная точка входа, подготовленная для будущего Telegram Mini App."
      />
      <div className="quick-action-list">
        {links.map((item) => (
          <Link href={item.href} key={item.href}>
            <Icon name={item.icon} />
            <div>
              <strong>{item.title}</strong>
              <span>{item.text}</span>
            </div>
            <Icon name="arrow" />
          </Link>
        ))}
      </div>
      <section className="workspace-section">
        <div className="form-panel">
          <h2>Проверка Telegram-пользователя</h2>
          <p>
            Эта страница пока использует обычную веб-сессию. При подключении Mini
            App параметр initData должен проверяться на сервере; данные из
            initDataUnsafe не используются как доверенный источник.
          </p>
        </div>
      </section>
    </div>
  );
}
