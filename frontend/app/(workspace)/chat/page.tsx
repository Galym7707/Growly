"use client";

import {
  FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon, type IconName } from "@/components/icons";
import { ReportPicker } from "@/components/report-picker";
import { SelectedReportCard } from "@/components/selected-report-card";
import { LoadingState, PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import {
  activeContextTopic,
  CHAT_PLACEHOLDER_NO_CONTEXT,
  chatMode,
  chatPlaceholderSource,
  chatRequestBody,
} from "@/lib/active-context";
import { useActiveContext } from "@/lib/active-context-provider";
import { reportPathFromGeneratedResponse } from "@/lib/generated-navigation";
import { useLanguage } from "@/lib/i18n";
import type { Report } from "@/lib/types";

type Action =
  | "market_scan"
  | "competitors"
  | "content_plan"
  | "create_post"
  | "drafts"
  | "reports"
  | "sources"
  | "notion_sync"
  | "ideas"
  | "ask";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  meta?: string;
};

const nicheActions: {
  id: Action;
  label: string;
  icon: IconName;
  placeholder: string;
}[] = [
  { id: "market_scan", label: "Анализ рынка", icon: "market", placeholder: "Опишите нишу, продукт и регион" },
  { id: "competitors", label: "Конкуренты", icon: "search", placeholder: "Укажите рынок или тему отчёта" },
  { id: "content_plan", label: "Контент-план", icon: "book", placeholder: "Опишите цель на неделю" },
  { id: "create_post", label: "Создать пост", icon: "draft", placeholder: "Передайте подробный бриф, канал и желаемый призыв" },
];

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
  const reportIdParam = searchParams.get("reportId");
  const { locale, t } = useLanguage();
  const { active, applyReport, loadActiveReport, clearActive } =
    useActiveContext();
  const activeTopic = activeContextTopic(active);

  const [skipReport, setSkipReport] = useState(false);
  const [pickingId, setPickingId] = useState<number | null>(null);
  const [hydrating, setHydrating] = useState(false);
  const [selectError, setSelectError] = useState(false);
  const [nicheAction, setNicheAction] = useState<Action>("market_scan");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const hydratedParam = useRef<string | null>(null);

  useEffect(() => {
    if (!reportIdParam || !/^\d+$/.test(reportIdParam)) return;
    if (hydratedParam.current === reportIdParam) return;
    if (active && active.report_id === Number(reportIdParam)) {
      hydratedParam.current = reportIdParam;
      return;
    }
    hydratedParam.current = reportIdParam;
    setSelectError(false);
    setHydrating(true);
    void loadActiveReport(Number(reportIdParam))
      .then((next) => {
        if (!next) setSelectError(true);
      })
      .finally(() => setHydrating(false));
  }, [reportIdParam, active, loadActiveReport]);

  useEffect(() => {
    const intro = active
      ? t(
          "Я работаю с отчётом «{topic}». Выберите действие или задайте вопрос по этому рынку.",
          { topic: activeTopic || t("отчёт") },
        )
      : t("Опишите нишу, продукт и регион — или вернитесь и выберите отчёт.");
    setMessages([{ id: 1, role: "assistant", text: intro }]);
  }, [active, activeTopic, t]);

  const selectedNiche = useMemo(
    () => nicheActions.find((item) => item.id === nicheAction) || nicheActions[0],
    [nicheAction],
  );

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
            answer?: string;
            report?: { id?: number; title?: string };
            items?: unknown[];
            draft?: { id?: number; title?: string };
          };
        }>("/chat", {
          method: "POST",
          body: JSON.stringify(
            chatRequestBody(active, actionId, message, context, locale),
          ),
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
        if (actionId === "competitors") {
          const target = reportPathFromGeneratedResponse(response.result);
          if (target) router.push(target);
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
    [active, locale, router, t],
  );

  async function saveActiveReportToNotion() {
    if (!active) return;
    setLoading(true);
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", text: t("Сохранить в Notion"), meta: t("Сохранить в Notion") },
    ]);
    try {
      await apiRequest("/notion/sync", {
        method: "POST",
        body: JSON.stringify({ target: "report", target_id: active.report_id }),
      });
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: "assistant", text: t("Сохранено в Notion"), meta: "completed" },
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

  function handleSelect(report: Report) {
    setSelectError(false);
    setPickingId(report.id);
    const next = applyReport(report);
    setPickingId(null);
    if (!next) {
      setSelectError(true);
      return;
    }
    setSkipReport(false);
    hydratedParam.current = String(report.id);
    router.replace(`/chat?reportId=${report.id}`);
  }

  function retrySelect() {
    setSelectError(false);
    hydratedParam.current = null;
    if (reportIdParam && /^\d+$/.test(reportIdParam)) {
      setHydrating(true);
      void loadActiveReport(Number(reportIdParam))
        .then((next) => {
          if (!next) setSelectError(true);
        })
        .finally(() => setHydrating(false));
    }
  }

  async function changeReport() {
    await clearActive();
    setSkipReport(false);
    setSelectError(false);
    hydratedParam.current = null;
    router.replace("/chat");
  }

  function submitWithReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = text.trim();
    if (!message) return;
    setText("");
    void runChat("ask", message, {}, t("Вопрос по отчёту"));
  }

  function submitNiche(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = text.trim() || t(selectedNiche.placeholder);
    setText("");
    void runChat(
      nicheAction,
      message,
      contextForAction(nicheAction, message, locale),
      t(selectedNiche.label),
    );
  }

  const placeholder = t(
    chatPlaceholderSource(active, CHAT_PLACEHOLDER_NO_CONTEXT),
  );

  const quickActions: { id: string; label: string; icon: IconName; run: () => void }[] =
    active
      ? [
          { id: "plan", label: "Создать контент-план", icon: "book", run: () => router.push(`/content-plan?reportId=${active.report_id}`) },
          { id: "ideas", label: "Показать идеи постов", icon: "report", run: () => void runChat("ideas", t("Показать идеи постов"), {}, t("Идеи постов")) },
          { id: "competitors", label: "Сформировать конкурентный вывод", icon: "search", run: () => void runChat("competitors", activeTopic || t("последний анализ рынка"), { query: activeTopic || "" }, t("Конкуренты")) },
          { id: "post", label: "Создать пост", icon: "draft", run: () => router.push(`/create-post?reportId=${active.report_id}`) },
          { id: "notion", label: "Сохранить в Notion", icon: "notion", run: () => void saveActiveReportToNotion() },
        ]
      : [];

  const showPicker = chatMode(active, skipReport) === "picker";

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Командный интерфейс")}
        title={t("Чат")}
        description={t("Быстрый доступ к основным действиям Growly без дублирования бизнес-логики.")}
      />

      {selectError ? (
        <div className="feedback feedback-error" role="alert">
          <p>{t("Не удалось выбрать отчёт. Попробуйте ещё раз.")}</p>
          <div className="feedback-actions">
            <button
              className="button button-secondary button-small"
              onClick={retrySelect}
              type="button"
            >
              {t("Повторить")}
            </button>
            {reportIdParam ? (
              <Link
                className="button button-secondary button-small"
                href={`/reports/${reportIdParam}`}
              >
                {t("Открыть отчёт")}
              </Link>
            ) : null}
            <button
              className="button button-secondary button-small"
              onClick={changeReport}
              type="button"
            >
              {t("Выбрать другой отчёт")}
            </button>
          </div>
        </div>
      ) : hydrating && !active ? (
        <LoadingState label={t("Загружаю контекст отчёта…")} />
      ) : showPicker ? (
        <ReportPicker
          title={t("Выберите отчёт, с которым будет работать чат")}
          manualLabel={t("Продолжить без отчёта")}
          onManual={() => setSkipReport(true)}
          onSelect={handleSelect}
          selectingId={pickingId}
        />
      ) : active ? (
        <div className="chat-workspace">
          <SelectedReportCard active={active} heading={t("Чат работает с отчётом")}>
            <Link
              className="button button-secondary button-small"
              href={`/reports/${active.report_id}`}
            >
              {t("Открыть отчёт")}
            </Link>
            <button
              className="button button-secondary button-small"
              onClick={() => void changeReport()}
              type="button"
            >
              {t("Изменить отчёт")}
            </button>
          </SelectedReportCard>

          <div className="quick-action-grid">
            {quickActions.map((item) => (
              <button
                className="quick-action"
                disabled={loading}
                key={item.id}
                onClick={item.run}
                type="button"
              >
                <Icon name={item.icon} />
                <span>{t(item.label)}</span>
              </button>
            ))}
          </div>

          <div className="chat-board">
            <div className="chat-messages" aria-live="polite">
              {messages.map((message) => (
                <article className={`message message-${message.role}`} key={message.id}>
                  <p>{message.text}</p>
                  {message.meta ? <small>{message.meta}</small> : null}
                </article>
              ))}
              {messages.length <= 1 && !loading ? (
                <p className="chat-empty-hint">
                  {t("Выберите быстрое действие выше или задайте вопрос ниже.")}
                </p>
              ) : null}
              {loading ? (
                <article className="message message-assistant">
                  <p>{t("Задача выполняется на сервере.")}</p>
                  <small>{t("Длительные операции могут занять несколько минут.")}</small>
                </article>
              ) : null}
            </div>
            <form className="chat-composer" onSubmit={submitWithReport}>
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
          </div>
        </div>
      ) : (
        <div className="chat-layout">
          <aside className="chat-actions">
            <h2>{t("Действия")}</h2>
            {nicheActions.map((item) => (
              <button
                className={nicheAction === item.id ? "active" : ""}
                key={item.id}
                onClick={() => setNicheAction(item.id)}
                type="button"
              >
                <Icon name={item.icon} />
                {t(item.label)}
              </button>
            ))}
          </aside>
          <section className="chat-panel">
            <div className="chat-messages" aria-live="polite">
              {messages.map((message) => (
                <article className={`message message-${message.role}`} key={message.id}>
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
            <form className="chat-composer" onSubmit={submitNiche}>
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
      )}
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

function describeResult(
  result:
    | {
        answer?: string;
        report?: { id?: number; title?: string };
        items?: unknown[];
        draft?: { id?: number; title?: string };
      }
    | undefined,
  t: (source: string, variables?: Record<string, string | number>) => string,
): string {
  if (!result) return t("Задача выполнена.");
  if (typeof result.answer === "string" && result.answer.trim()) {
    return result.answer;
  }
  if (result.report) {
    return t("Отчёт готов: {name}. Откройте раздел «Отчёты» для просмотра.", {
      name: result.report.title || `ID ${result.report.id}`,
    });
  }
  if (result.draft) {
    return t("Черновик создан: {name}. Он доступен в разделе «Черновики».", {
      name: result.draft.title || `ID ${result.draft.id}`,
    });
  }
  if (Array.isArray(result.items)) {
    return t("Готово. Получено элементов: {count}.", { count: result.items.length });
  }
  return t("Задача выполнена.");
}
