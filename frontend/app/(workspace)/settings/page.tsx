"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

type WorkspaceSettings = {
  business_name: string | null;
  business_niche: string | null;
  business_region: string | null;
  business_language: string | null;
  business_brand_tone: string | null;
  business_telegram_channel: string | null;
  business_notion_root: string | null;
};

const emptySettings: WorkspaceSettings = {
  business_name: "",
  business_niche: "",
  business_region: "",
  business_language: "Русский",
  business_brand_tone: "",
  business_telegram_channel: "",
  business_notion_root: "",
};

export default function SettingsPage() {
  const [values, setValues] = useState<WorkspaceSettings>(emptySettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const { t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ settings: WorkspaceSettings }>(
        "/settings",
      );
      setValues({ ...emptySettings, ...response.settings });
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(key: keyof WorkspaceSettings, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const response = await apiRequest<{ settings: WorkspaceSettings }>(
        "/settings",
        {
          method: "PATCH",
          body: JSON.stringify(values),
        },
      );
      setValues(response.settings);
      setSaved(true);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Конфигурация")}
        title={t("Настройки")}
        description={t("Профиль бизнеса и ссылки на подключённые рабочие пространства.")}
      />
      {loading ? <LoadingState /> : null}
      {error && loading ? <ErrorState message={error} retry={load} /> : null}
      {!loading ? (
        <form className="form-panel" onSubmit={submit}>
          <h2>{t("Профиль бизнеса")}</h2>
          <p>
            {t("Эти данные используются при подготовке планов и материалов. Секретные ключи на этой странице не отображаются.")}
          </p>
          <div className="form-grid">
            <label>
              <span>{t("Название")}</span>
              <input
                onChange={(event) =>
                  update("business_name", event.target.value)
                }
                value={values.business_name || ""}
              />
            </label>
            <label>
              <span>{t("Ниша")}</span>
              <input
                onChange={(event) =>
                  update("business_niche", event.target.value)
                }
                value={values.business_niche || ""}
              />
            </label>
            <label>
              <span>{t("Регион")}</span>
              <input
                onChange={(event) =>
                  update("business_region", event.target.value)
                }
                value={values.business_region || ""}
              />
            </label>
            <label>
              <span>{t("Язык")}</span>
              <input
                onChange={(event) =>
                  update("business_language", event.target.value)
                }
                value={values.business_language || ""}
              />
            </label>
            <label className="full">
              <span>{t("Тон бренда")}</span>
              <textarea
                onChange={(event) =>
                  update("business_brand_tone", event.target.value)
                }
                placeholder={t("Например: спокойно, предметно, без громких обещаний")}
                value={values.business_brand_tone || ""}
              />
            </label>
            <label>
              <span>{t("Telegram-канал")}</span>
              <input
                onChange={(event) =>
                  update("business_telegram_channel", event.target.value)
                }
                placeholder="@channel или chat ID"
                value={values.business_telegram_channel || ""}
              />
            </label>
            <label>
              <span>{t("Корневая страница Notion")}</span>
              <input
                onChange={(event) =>
                  update("business_notion_root", event.target.value)
                }
                placeholder="URL или ID без API-ключа"
                value={values.business_notion_root || ""}
              />
            </label>
          </div>
          {error ? <div className="feedback feedback-error">{error}</div> : null}
          {saved ? (
            <div className="feedback feedback-success">
              {t("Настройки сохранены.")}
            </div>
          ) : null}
          <div className="form-actions">
            <button className="button button-primary" disabled={saving}>
              <Icon name={saving ? "sync" : "check"} />
              {t(saving ? "Сохраняем" : "Сохранить")}
            </button>
          </div>
        </form>
      ) : null}
      <section className="workspace-section">
        <div className="form-panel">
          <h2>{t("Режим рабочего пространства")}</h2>
          <p>
            {t("Веб-кабинет использует Supabase Auth и хранит рабочие данные отдельно для каждого аккаунта.")}
          </p>
        </div>
      </section>
    </div>
  );
}
