"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { Status } from "@/components/ui";
import { apiRequest, formatDate } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import {
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
  nextTaskStatus,
  type ContentTask,
  type TaskPriority,
} from "@/lib/tasks";
import { useWorkspace } from "@/lib/workspace";

export function TasksPanel({
  title,
  source,
  limit,
}: {
  title?: string;
  source?: { source_type: "content_plan" | "report" | "draft"; source_id: number };
  limit?: number;
}) {
  const { locale, t } = useLanguage();
  const { workspace } = useWorkspace();
  const canEdit = Boolean(workspace?.permissions.can_edit);

  const [tasks, setTasks] = useState<ContentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAssignee, setNewAssignee] = useState("");
  const [newDue, setNewDue] = useState("");
  const [newPriority, setNewPriority] = useState<TaskPriority>("medium");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiRequest<{ items: ContentTask[] }>("/tasks");
      setTasks(response.items || []);
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function addTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTitle.trim()) return;
    setAdding(true);
    setError("");
    try {
      await apiRequest("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle.trim(),
          assignee_email: newAssignee.trim() || null,
          due_date: newDue || null,
          priority: newPriority,
          source_type: source?.source_type || "manual",
          source_id: source?.source_id ?? null,
        }),
      });
      setNewTitle("");
      setNewAssignee("");
      setNewDue("");
      setNewPriority("medium");
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setAdding(false);
    }
  }

  async function advance(task: ContentTask) {
    if (!canEdit) return;
    setBusyId(task.id);
    try {
      await apiRequest(`/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextTaskStatus(task.status) }),
      });
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(task: ContentTask) {
    if (!canEdit) return;
    setBusyId(task.id);
    try {
      await apiRequest(`/tasks/${task.id}`, { method: "DELETE" });
      await load();
    } catch (value) {
      setError(value instanceof Error ? t(value.message) : t("Неизвестная ошибка"));
    } finally {
      setBusyId(null);
    }
  }

  const visible = limit ? tasks.slice(0, limit) : tasks;

  return (
    <div className="tasks-panel">
      {title ? <h2>{t(title)}</h2> : null}

      {loading ? (
        <p className="muted">{t("Загрузка данных")}…</p>
      ) : visible.length ? (
        <ul className="task-list">
          {visible.map((task) => (
            <li className={`task-item task-${task.status}`} key={task.id}>
              <button
                aria-label={t("Изменить статус")}
                className="task-check"
                disabled={!canEdit || busyId === task.id}
                onClick={() => advance(task)}
                type="button"
              >
                <Icon name={task.status === "done" ? "check" : "chevron"} />
              </button>
              <div className="task-body">
                <span className="task-title">{task.title}</span>
                <span className="task-meta muted">
                  {task.assignee_email ? <>{task.assignee_email} · </> : null}
                  {task.due_date ? formatDate(task.due_date, locale) : t("Без срока")}
                  {" · "}
                  {t(TASK_PRIORITY_LABELS[task.priority])}
                </span>
              </div>
              <Status value={task.status === "done" ? "active" : "pending"}>
                {t(TASK_STATUS_LABELS[task.status])}
              </Status>
              {canEdit ? (
                <button
                  aria-label={t("Удалить")}
                  className="icon-button"
                  disabled={busyId === task.id}
                  onClick={() => remove(task)}
                  type="button"
                >
                  <Icon name="close" />
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="inline-empty">{t("Задач пока нет.")}</p>
      )}

      {error ? <p className="form-error">{error}</p> : null}

      {canEdit ? (
        <form className="task-add" onSubmit={addTask}>
          <input
            onChange={(event) => setNewTitle(event.target.value)}
            placeholder={t("Что нужно сделать?")}
            value={newTitle}
          />
          <input
            onChange={(event) => setNewAssignee(event.target.value)}
            placeholder={t("Ответственный (email)")}
            type="email"
            value={newAssignee}
          />
          <input
            aria-label={t("Срок")}
            onChange={(event) => setNewDue(event.target.value)}
            type="date"
            value={newDue}
          />
          <select
            aria-label={t("Приоритет")}
            onChange={(event) => setNewPriority(event.target.value as TaskPriority)}
            value={newPriority}
          >
            <option value="low">{t(TASK_PRIORITY_LABELS.low)}</option>
            <option value="medium">{t(TASK_PRIORITY_LABELS.medium)}</option>
            <option value="high">{t(TASK_PRIORITY_LABELS.high)}</option>
          </select>
          <button
            className="button button-primary button-small"
            disabled={adding || !newTitle.trim()}
            type="submit"
          >
            <Icon name={adding ? "sync" : "plus"} />
            {t("Создать задачу")}
          </button>
        </form>
      ) : null}
    </div>
  );
}
