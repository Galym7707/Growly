import Link from "next/link";
import type { ReactNode } from "react";
import { Icon, type IconName } from "@/components/icons";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {action}
    </header>
  );
}

export function Status({
  value,
  children,
}: {
  value: string;
  children?: ReactNode;
}) {
  const normalized = value.toLowerCase();
  const labels: Record<string, string> = {
    active: "Активен",
    analysis_pending: "Ожидает анализа",
    approved: "Согласован",
    completed: "Завершён",
    disabled: "Отключён",
    draft: "Черновик",
    drafted: "Черновик создан",
    failed: "Ошибка",
    pending: "На согласовании",
    published: "Опубликован",
    ready: "Готов",
    rejected: "Отклонён",
    requires_review: "Требует проверки",
    running: "Выполняется",
  };
  const tone =
    normalized.includes("ready") ||
    normalized.includes("active") ||
    normalized.includes("approved") ||
    normalized.includes("published") ||
    normalized.includes("completed")
      ? "positive"
      : normalized.includes("fail") ||
          normalized.includes("reject") ||
          normalized.includes("disabled")
        ? "negative"
        : "neutral";
  const customLabel =
    typeof children === "string" && children !== value ? children : null;
  return (
    <span className={`status status-${tone}`}>
      {customLabel || labels[normalized] || children || value}
    </span>
  );
}

export function EmptyState({
  icon,
  title,
  text,
  href,
  action,
}: {
  icon: IconName;
  title: string;
  text: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name={icon} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
      {href && action ? (
        <Link className="button button-secondary" href={href}>
          {action}
          <Icon name="arrow" />
        </Link>
      ) : null}
    </div>
  );
}

export function LoadingState({ label = "Загрузка данных" }: { label?: string }) {
  return (
    <div className="loading-state" aria-live="polite">
      <span />
      <span />
      <span />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <strong>Не удалось загрузить данные</strong>
      <p>{message}</p>
      {retry ? (
        <button className="button button-secondary" onClick={retry} type="button">
          Повторить
        </button>
      ) : null}
    </div>
  );
}
