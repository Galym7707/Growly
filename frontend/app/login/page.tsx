"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Icon } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { isLocalAuthBypassAllowed } from "@/lib/auth-config";
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
  const [mode, setMode] = useState<"login" | "register">(
    searchParams.get("mode") === "register" ? "register" : "login",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const configured = isSupabaseConfigured();
  const localModeAllowed = isLocalAuthBypassAllowed();
  const { t } = useLanguage();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPath = getSafeNextPath(searchParams.get("next"));
    if (!configured) {
      if (localModeAllowed) {
        router.push(nextPath);
      }
      return;
    }
    setLoading(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const { data, error: authError } =
      mode === "register"
        ? await supabase.auth.signUp({
            email,
            password,
            options: {
              emailRedirectTo: `${window.location.origin}${nextPath}`,
            },
          })
        : await supabase.auth.signInWithPassword({
            email,
            password,
          });
    setLoading(false);
    if (authError) {
      setError(
        t(
          mode === "register"
            ? "Не удалось зарегистрироваться. Проверьте почту и пароль."
            : "Не удалось войти. Проверьте почту и пароль.",
        ),
      );
      return;
    }
    if (mode === "register" && !data.session) {
      setNotice(t("Проверьте почту, чтобы подтвердить регистрацию."));
      return;
    }
    router.push(nextPath);
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
              mode === "register"
                ? "Создайте аккаунт, чтобы работать только со своими данными."
                : "Войдите, чтобы продолжить работу с источниками, планами и согласованием материалов.",
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
          <p className="eyebrow">{t(mode === "register" ? "Регистрация" : "Вход")}</p>
          <h2>
            {t(
              mode === "register"
                ? "Создать рабочую область"
                : "Открыть рабочую область",
            )}
          </h2>
          {!configured ? (
            <div className="notice">
              {t(
                localModeAllowed
                  ? "Supabase Auth не настроен. В локальном режиме можно открыть интерфейс без авторизации."
                  : "Supabase Auth не настроен. Вход в рабочую область временно недоступен.",
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
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              disabled={!configured}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t("Пароль")}
              required={configured}
              type="password"
              value={password}
            />
          </label>
          {notice ? <div className="notice">{notice}</div> : null}
          {error ? <p className="form-error">{error}</p> : null}
          <button
            className="button button-primary button-wide"
            disabled={loading || (!configured && !localModeAllowed)}
          >
            {loading
              ? t(mode === "register" ? "Создаём аккаунт" : "Проверяем доступ")
              : configured
                ? t(mode === "register" ? "Зарегистрироваться" : "Войти")
                : localModeAllowed
                  ? t("Открыть локальный режим")
                  : t("Вход временно недоступен")}
            <Icon name="arrow" />
          </button>
          {configured ? (
            <button
              className="auth-switch"
              onClick={() => {
                setMode((current) =>
                  current === "login" ? "register" : "login",
                );
                setError("");
                setNotice("");
              }}
              type="button"
            >
              {t(
                mode === "register"
                  ? "Уже есть аккаунт? Войти"
                  : "Нет аккаунта? Зарегистрироваться",
              )}
            </button>
          ) : null}
        </form>
      </div>
    </main>
  );
}

function getSafeNextPath(next: string | null): string {
  if (next?.startsWith("/") && !next.startsWith("//")) return next;
  return "/dashboard";
}
