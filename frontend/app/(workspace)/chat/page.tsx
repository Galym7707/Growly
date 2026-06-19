"use client";

import {
  FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon, type IconName } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { apiRequest, formatDate } from "@/lib/api";
import { activeContextTopic, chatPlaceholderSource } from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import {
  contentPlanPathFromGeneratedResponse,
  extractGeneratedContentPlanId,
  extractGeneratedDraftId,
  reportPathFromGeneratedResponse,
} from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";

type Action =
  | "market_scan"
  | "competitors"
  | "content_plan"
  | "create_post"
  | "drafts"
  | "reports"
  | "sources"
  | "notion_sync";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  meta?: string;
};

const actions: {
  id: Action;
  label: string;
  icon: IconName;
  placeholder: string;
}[] = [
  {
    id: "market_scan",
    label: "Анализ рынка",
    icon: "market",
    placeholder: "Опишите нишу, продукт и регион",
  },
  {
    id: "competitors",
    label: "Конкуренты",
    icon: "search",
    placeholder: "Укажите рынок или тему отчёта",
  },
  {
    id: "content_plan",
    label: "Контент-план",
    icon: "book",
    placeholder: "Опишите цель на неделю",
  },
  {
    id: "create_post",
    label: "Создать пост",
    icon: "draft",
    placeholder: "Передайте подробный бриф, канал и желаемый призыв",
  },
  {
    id: "drafts",
    label: "Черновики",
    icon: "draft",
    placeholder: "Показать последние черновики",
  },
  {
    id: "reports",
    label: "Отчёты",
    icon: "report",
    placeholder: "Показать последние отчёты",
  },
  {
    id: "sources",
    label: "Источники",
    icon: "source",
    placeholder: "Показать сохранённые источники",
  },
  {
    id: "notion_sync",
    label: "Сохранить в Notion",
    icon: "notion",
    placeholder: "Синхронизировать последние данные",
  },
];

const INTRO_NO_CONTEXT =
  "Выберите действие слева и опишите задачу. Growly вызовет тот же сервисный слой, который используется Telegram-ботом.";

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="workspace-page" />}>
      <ChatContent />
    </Suspense>
  );
}

function ChatContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedAction = searchParams.get("action") as Action | null;
  const [action, setAction] = useState<Action>(
    actions.some((item) => item.id === requestedAction)
      ? requestedAction!
      : "market_scan",
  );
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const { locale, t } = useLanguage();
  const { active } = useActiveContext();
  const activeTopic = activeContextTopic(active);
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: "assistant", text: t(INTRO_NO_CONTEXT) },
  ]);

  useEffect(() => {
    const intro = active
      ? t(
          "Последний анализ: {topic}. Источников: {count}. Что хотите сделать дальше?",
          {
            topic: activeTopic || t("анализ рынка"),
            count: active.sources_count,
          },
        )
      : t(INTRO_NO_CONTEXT);
    setMessages((current) =>
      current.map((message) =>
        message.id === 1 ? { ...message, text: intro } : message,
      ),
    );
  }, [active, activeTopic, t]);

  const selected = useMemo(
    () => actions.find((item) => item.id === action)!,
    [action],
  );

  useEffect(() => {
    if (actions.some((item) => item.id === requestedAction)) {
      setAction(requestedAction!);
    }
  }, [requestedAction]);

  const runChat = useCallback(
    async (
      actionId: Action,
      message: string,
      context: Record<string, unknown>,
      metaLabel: string,
    ) => {
      setMessages((current) => [
        ...current,
        { id: Date.now(), role: "user", text: message, meta: metaLabel },
      ]);
      setLoading(true);
      try {
        const response = await apiRequest<{
          message: string;
          status: string;
          result?: {
            report?: { id?: number; title?: string };
            items?: unknown[];
            draft?: { id?: number; title?: string };
            counts?: Record<string, number>;
          };
        }>("/chat", {
          method: "POST",
          body: JSON.stringify({
            action: actionId,
            message,
            context,
            language: locale,
          }),
        });
        setMessages((current) => [
          ...current,
          {
            id: Date.now() + 1,
            role: "assistant",
            text: describeResult(response.result, t),
            meta: response.status,
          },
        ]);
        const target = generatedNavigationTarget(actionId, response.result);
        if (target) {
          router.push(target);
        }
      } catch (value) {
        setMessages((current) => [
          ...current,
          {
            id: Date.now() + 1,
            role: "assistant",
            text:
              value instanceof Error
                ? t(value.message)
                : t("Задачу не удалось выполнить."),
            meta: t("Ошибка"),
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [locale, router, t],
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = text.trim() || t(selected.placeholder);
    setText("");
    void runChat(action, message, contextForAction(action, message, locale), t(selected.label));
  }

  async function saveActiveReportToNotion() {
    if (!active) return;
    setLoading(true);
    setMessages((current) => [
      ...current,
      {
        id: Date.now(),
        role: "user",
        text: t("Сохранить в Notion"),
        meta: t("Сохранить в Notion"),
      },
    ]);
    try {
      await apiRequest("/notion/sync", {
        method: "POST",
        body: JSON.stringify({ target: "report", target_id: active.report_id }),
      });
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: t("Сохранено в Notion"),
          meta: "completed",
        },
      ]);
    } catch (value) {
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: value instanceof Error ? t(value.message) : t("Неизвестная ошибка"),
          meta: t("Ошибка"),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const quickActions: { id: string; label: string; icon: IconName; run: () => void }[] =
    active
      ? [
          {
            id: "content_plan",
            label: "Создать контент-план",
            icon: "book",
            run: () => router.push("/content-plan"),
          },
          {
            id: "create_post",
            label: "Создать пост",
            icon: "draft",
            run: () => router.push("/create-post"),
          },
          {
            id: "ideas",
            label: "Показать идеи",
            icon: "report",
            run: () => router.push(`/reports/${active.report_id}`),
          },
          {
            id: "competitors",
            label: "Сформировать конкурентный отчёт",
            icon: "search",
            run: () =>
              void runChat(
                "competitors",
                activeTopic || t("последний анализ рынка"),
                { query: activeTopic || "" },
                t("Конкуренты"),
              ),
          },
          {
            id: "notion",
            label: "Сохранить в Notion",
            icon: "notion",
            run: () => void saveActiveReportToNotion(),
          },
          {
            id: "open",
            label: "Открыть отчёт",
            icon: "arrow",
            run: () => router.push(`/reports/${active.report_id}`),
          },
        ]
      : [];

  const placeholder = t(chatPlaceholderSource(active, selected.placeholder));

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Командный интерфейс")}
        title={t("Чат")}
        description={t("Быстрый доступ к основным действиям Growly без дублирования бизнес-логики.")}
      />
      <div className="chat-layout">
        <aside className="chat-actions">
          <h2>{t("Действия")}</h2>
          {actions.map((item) => (
            <button
              className={action === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setAction(item.id)}
              type="button"
            >
              <Icon name={item.icon} />
              {t(item.label)}
            </button>
          ))}
        </aside>
        <section className="chat-panel">
          {active ? (
            <div className="chat-context">
              <div className="chat-context-head">
                <p className="eyebrow">{t("Последний анализ")}</p>
                <h2>{activeTopic || t("Анализ рынка")}</h2>
                <p className="chat-context-meta">
                  {t("{count} источников", { count: active.sources_count })}
                  {active.created_at
                    ? ` · ${formatDate(active.created_at, locale)}`
                    : ""}
                </p>
              </div>
              <div className="chat-quick-actions">
                {quickActions.map((item) => (
                  <button
                    className="button button-secondary button-small"
                    disabled={loading}
                    key={item.id}
                    onClick={item.run}
                    type="button"
                  >
                    <Icon name={item.icon} />
                    {t(item.label)}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          <div className="chat-messages" aria-live="polite">
            {messages.map((message) => (
              <article
                className={`message message-${message.role}`}
                key={message.id}
              >
                <p>{message.text}</p>
                {message.meta ? <small>{message.meta}</small> : null}
              </article>
            ))}
            {loading ? (
              <article className="message message-assistant">
                <p>{t("Задача выполняется на сервере.")}</p>
                <small>{t("Длительные операции могут занять несколько минут.")}</small>
              </article>
            ) : null}
          </div>
          <form className="chat-composer" onSubmit={submit}>
            <textarea
              aria-label={t("Сообщение")}
              onChange={(event) => setText(event.target.value)}
              placeholder={placeholder}
              value={text}
            />
            <button className="button button-primary" disabled={loading}>
              <Icon name="arrow" />
              {t("Отправить")}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

function contextForAction(
  action: Action,
  message: string,
  locale: string,
): Record<string, unknown> {
  if (action === "market_scan") {
    return {
      niche: message,
      region_language:
        locale === "en"
          ? "Kazakhstan, English"
          : locale === "kk"
            ? "Қазақстан, қазақ тілі"
            : "Казахстан, русский язык",
    };
  }
  if (action === "content_plan") return { weekly_objective: message };
  if (action === "create_post") return { brief: message, channel: "Telegram" };
  return {};
}

function generatedNavigationTarget(
  action: Action,
  result:
    | {
        report?: { id?: number; title?: string };
        items?: unknown[];
        draft?: { id?: number; title?: string };
      }
    | undefined,
): string | null {
  if (!result) return null;
  if (action === "market_scan" || action === "competitors") {
    return reportPathFromGeneratedResponse(result);
  }
  if (action === "content_plan" && extractGeneratedContentPlanId(result)) {
    return contentPlanPathFromGeneratedResponse(result) || "/content-plan";
  }
  if (action === "create_post" && extractGeneratedDraftId(result)) {
    return "/drafts";
  }
  return null;
}

function describeResult(
  result:
    | {
        report?: { id?: number; title?: string };
        items?: unknown[];
        draft?: { id?: number; title?: string };
        counts?: Record<string, number>;
      }
    | undefined,
  t: (source: string, variables?: Record<string, string | number>) => string,
): string {
  if (!result) return t("Задача выполнена.");
  if (result.report) {
    return t(
      "Отчёт готов: {name}. Откройте раздел «Отчёты» для просмотра.",
      { name: result.report.title || `ID ${result.report.id}` },
    );
  }
  if (result.draft) {
    return t(
      "Черновик создан: {name}. Он доступен в разделе «Черновики».",
      { name: result.draft.title || `ID ${result.draft.id}` },
    );
  }
  if (Array.isArray(result.items)) {
    return t("Готово. Получено элементов: {count}.", {
      count: result.items.length,
    });
  }
  if (result.counts) {
    const total = Object.values(result.counts).reduce(
      (sum, value) => sum + value,
      0,
    );
    return t("Синхронизация Notion завершена. Обработано объектов: {count}.", {
      count: total,
    });
  }
  return t("Задача выполнена.");
}
