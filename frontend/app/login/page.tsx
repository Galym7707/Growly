"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Icon } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { useLanguage } from "@/lib/i18n";
import {
  createClient,
  isSupabaseConfigured,
} from "@/lib/supabase/client";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="auth-page" />}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const configured = isSupabaseConfigured();
  const { t } = useLanguage();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!configured) {
      router.push("/dashboard");
      return;
    }
    setLoading(true);
    setError("");
    const { error: authError } = await createClient().auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (authError) {
      setError(t("Не удалось войти. Проверьте почту и пароль."));
      return;
    }
    router.push(searchParams.get("next") || "/dashboard");
    router.refresh();
  }

  return (
    <main className="auth-page">
      <div className="auth-brand">
        <Logo />
        <LanguageSwitcher compact />
        <div>
          <p className="eyebrow">{t("Рабочее пространство Growly")}</p>
          <h1>{t("Рынок, отчёты и контент в одном процессе.")}</h1>
          <p>
            {t(
              "Войдите, чтобы продолжить работу с источниками, планами и согласованием материалов.",
            )}
          </p>
        </div>
        <Link className="text-link" href="/">
          {t("Вернуться на главную")}
          <Icon name="arrow" />
        </Link>
      </div>
      <div className="auth-panel">
        <form onSubmit={submit}>
          <p className="eyebrow">{t("Вход")}</p>
          <h2>{t("Открыть рабочую область")}</h2>
          {!configured ? (
            <div className="notice">
              {t(
                "Supabase Auth не настроен. В локальном режиме можно открыть интерфейс без авторизации.",
              )}
            </div>
          ) : null}
          <label>
            <span>{t("Рабочая почта")}</span>
            <input
              autoComplete="email"
              disabled={!configured}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@company.kz"
              required={configured}
              type="email"
              value={email}
            />
          </label>
          <label>
            <span>{t("Пароль")}</span>
            <input
              autoComplete="current-password"
              disabled={!configured}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t("Пароль")}
              required={configured}
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button button-primary button-wide" disabled={loading}>
            {loading
              ? t("Проверяем доступ")
              : configured
                ? t("Войти")
                : t("Открыть локальный режим")}
            <Icon name="arrow" />
          </button>
        </form>
      </div>
    </main>
  );
}
