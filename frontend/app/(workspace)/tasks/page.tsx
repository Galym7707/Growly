"use client";

import { PageHeader } from "@/components/ui";
import { TasksPanel } from "@/components/tasks/tasks-panel";
import { useLanguage } from "@/lib/i18n";

export default function TasksPage() {
  const { t } = useLanguage();
  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Команда")}
        title={t("Задачи")}
        description={t("Что нужно сделать команде: ответственные, сроки и статусы.")}
      />
      <section className="workspace-section">
        <div className="form-panel">
          <TasksPanel />
        </div>
      </section>
    </div>
  );
}
