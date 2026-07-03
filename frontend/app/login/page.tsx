"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
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

  useEffect(() => {
    if (searchParams.get("error") === "oauth") {
      setError(t("Не удалось войти через Google. Попробуйте ещё раз."));
    }
  }, [searchParams, t]);

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

    if (mode === "register") {
      // Server-side sign-up creates a pre-confirmed account, so no
      // confirmation email is sent and Supabase SMTP rate limits cannot
      // block registration.
      let registered = false;
      try {
        const response = await fetch("/api/growly/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (response.ok) {
          registered = true;
        } else if (response.status === 409) {
          setNotice(t("Аккаунт с этой почтой уже существует. Выполняем вход."));
          registered = true;
        } else if (response.status !== 404 && response.status !== 502) {
          const body = await response.json().catch(() => ({}));
          setLoading(false);
          setError(
            typeof body.detail === "string" && body.detail
              ? t(body.detail)
              : t("Не удалось зарегистрироваться. Проверьте почту и пароль."),
          );
          return;
        }
      } catch {
        // Backend unreachable: fall through to the legacy sign-up below.
      }
      if (!registered) {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}${nextPath}`,
          },
        });
        setLoading(false);
        if (signUpError) {
          setError(describeAuthError(signUpError.message, t));
          return;
        }
        if (!data.session) {
          setNotice(t("Проверьте почту, чтобы подтвердить регистрацию."));
          return;
        }
        router.push(nextPath);
        router.refresh();
        return;
      }
    }

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (authError) {
      setError(
        mode === "register"
          ? describeAuthError(authError.message, t)
          : t("Не удалось войти. Проверьте почту и пароль."),
      );
      return;
    }
    router.push(nextPath);
    router.refresh();
  }

  async function signInWithGoogle() {
    if (!configured) return;
    const nextPath = getSafeNextPath(searchParams.get("next"));
    setLoading(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`,
      },
    });
    if (oauthError) {
      setLoading(false);
      setError(t("Не удалось открыть вход через Google. Попробуйте позже."));
    }
    // On success the browser navigates away to Google.
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
            <>
              <div className="auth-divider">
                <span>{t("или")}</span>
              </div>
              <button
                className="button button-secondary button-wide auth-google"
                disabled={loading}
                onClick={signInWithGoogle}
                type="button"
              >
                <GoogleMark />
                {t("Продолжить с Google")}
              </button>
            </>
          ) : null}
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
              <span>
                {t(
                  mode === "register"
                    ? "Уже есть аккаунт? Войти"
                    : "Нет аккаунта? Зарегистрироваться",
                )}
              </span>
              <Icon name="arrow" />
            </button>
          ) : null}
        </form>
      </div>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg aria-hidden="true" height="18" viewBox="0 0 48 48" width="18">
      <path
        d="M44 24.5c0-1.6-.1-2.8-.4-4H24v7.6h11.4c-.2 1.9-1.5 4.8-4.4 6.7l-.04.27 6.4 4.96.44.04C41.9 35.9 44 30.7 44 24.5z"
        fill="#4285F4"
      />
      <path
        d="M24 44c5.9 0 10.9-1.9 14.5-5.3l-6.9-5.3c-1.9 1.3-4.5 2.3-7.6 2.3-5.8 0-10.7-3.9-12.5-9.2l-.25.02-6.65 5.16-.09.24C8 39.5 15.4 44 24 44z"
        fill="#34A853"
      />
      <path
        d="M11.5 26.5c-.5-1.4-.7-2.9-.7-4.5s.3-3.1.7-4.5l-.02-.3-6.74-5.24-.22.1A19.9 19.9 0 002 22c0 3.2.8 6.3 2.2 9l7.3-4.5z"
        fill="#FBBC05"
      />
      <path
        d="M24 9.8c4.1 0 6.9 1.8 8.5 3.3l6.2-6C34.9 3.6 29.9 2 24 2 15.4 2 8 6.5 4.2 13l7.3 5.6C13.3 13.7 18.2 9.8 24 9.8z"
        fill="#EA4335"
      />
    </svg>
  );
}

function getSafeNextPath(next: string | null): string {
  if (next?.startsWith("/") && !next.startsWith("//")) return next;
  return "/dashboard";
}

function describeAuthError(
  message: string,
  t: (source: string) => string,
): string {
  const normalized = (message || "").toLowerCase();
  if (normalized.includes("rate limit")) {
    return t(
      "Слишком много попыток регистрации. Подождите несколько минут и попробуйте снова.",
    );
  }
  if (normalized.includes("already registered") || normalized.includes("already exists")) {
    return t("Аккаунт с этой почтой уже существует. Войдите вместо регистрации.");
  }
  if (normalized.includes("password")) {
    return t("Пароль слишком простой. Используйте не менее 8 символов.");
  }
  return t("Не удалось зарегистрироваться. Проверьте почту и пароль.");
}
