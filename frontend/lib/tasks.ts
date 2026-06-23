export type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high";

export type ContentTask = {
  id: number;
  workspace_id: string;
  source_type: "report" | "content_plan" | "draft" | "manual";
  source_id: number | null;
  title: string;
  description: string | null;
  assignee_email: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "К выполнению",
  in_progress: "В работе",
  done: "Готово",
  cancelled: "Отменено",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
};

/** The next status when a user advances a task (todo → in_progress → done). */
export function nextTaskStatus(status: TaskStatus): TaskStatus {
  if (status === "todo") return "in_progress";
  if (status === "in_progress") return "done";
  return "todo";
}
