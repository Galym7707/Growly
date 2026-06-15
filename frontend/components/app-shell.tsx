"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { useLanguage } from "@/lib/i18n";
import {
  createClient,
  isSupabaseConfigured,
} from "@/lib/supabase/client";

const nav: { href: string; label: string; icon: IconName }[] = [
  { href: "/dashboard", label: "Обзор", icon: "home" },
  { href: "/chat", label: "Чат", icon: "chat" },
  { href: "/market-scan", label: "Анализ рынка", icon: "market" },
  { href: "/reports", label: "Отчёты", icon: "report" },
  { href: "/content-plan", label: "Контент-план", icon: "book" },
  { href: "/drafts", label: "Черновики", icon: "draft" },
  { href: "/sources", label: "Источники", icon: "source" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { t } = useLanguage();

  async function signOut() {
    if (isSupabaseConfigured()) {
      await createClient().auth.signOut();
    }
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <Logo compact />
        <button
          aria-label={t(open ? "Закрыть меню" : "Открыть меню")}
          className="icon-button"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          <Icon name={open ? "close" : "bars"} />
        </button>
      </header>
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="sidebar-top">
          <Logo compact />
          <span className="workspace-label">{t("Рабочее пространство")}</span>
        </div>
        <nav className="sidebar-nav" aria-label={t("Основная навигация")}>
          {nav.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                className={active ? "active" : ""}
                href={item.href}
                key={item.href}
                onClick={() => setOpen(false)}
              >
                <Icon name={item.icon} />
                <span>{t(item.label)}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <LanguageSwitcher />
          <Link
            className={pathname === "/settings" ? "active" : ""}
            href="/settings"
            onClick={() => setOpen(false)}
          >
            <Icon name="settings" />
            <span>{t("Настройки")}</span>
          </Link>
          <button onClick={signOut} type="button">
            <Icon name="arrow" />
            <span>{t("Выйти")}</span>
          </button>
        </div>
      </aside>
      {open ? (
        <button
          aria-label={t("Закрыть меню")}
          className="sidebar-backdrop"
          onClick={() => setOpen(false)}
          type="button"
        />
      ) : null}
      <main className="app-main">{children}</main>
    </div>
  );
}
