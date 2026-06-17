import type { Locale } from "./i18n";

type ContentPlanCopy = {
  basedOn: string;
  count: (count: number) => string;
  createDraft: string;
  created: string;
  creating: string;
  emptyTitle: string;
  emptyText: string;
  goalPlaceholder: string;
  manualCreate: string;
  newPlan: string;
  openReports: string;
  retry: string;
  runMarketScan: string;
  table: {
    date: string;
    channel: string;
    topic: string;
    goal: string;
    format: string;
    cta: string;
    source: string;
    status: string;
  };
  unknown: string;
  untitled: string;
};

export function contentPlanCopy(locale: Locale): ContentPlanCopy {
  if (locale === "en") {
    return {
      basedOn: "Data source",
      count: (count) => `Total: ${count}`,
      createDraft: "Draft",
      created: "Created",
      creating: "Creating",
      emptyTitle: "No content plan yet",
      emptyText: "No content plan yet. Create one from the latest market scan.",
      goalPlaceholder:
        "Example: explain the service value and collect consultation requests",
      manualCreate: "Create manually",
      newPlan: "New plan",
      openReports: "Open reports",
      retry: "Retry",
      runMarketScan: "Run market scan",
      table: {
        date: "Date",
        channel: "Channel",
        topic: "Topic",
        goal: "Goal",
        format: "Format",
        cta: "Call to action",
        source: "Idea source",
        status: "Status",
      },
      unknown: "Not specified",
      untitled: "Untitled",
    };
  }
  if (locale === "kk") {
    return {
      basedOn: "Дерек көзі",
      count: (count) => `Барлығы: ${count}`,
      createDraft: "Черновик",
      created: "Жасалды",
      creating: "Жасалуда",
      emptyTitle: "Контент-жоспар жоқ",
      emptyText:
        "Әзірге контент-жоспар жоқ. Соңғы нарық талдауы негізінде жоспар жасаңыз.",
      goalPlaceholder:
        "Мысалы: қызмет құндылығын түсіндіріп, консультацияға өтінім жинау",
      manualCreate: "Қолмен жасау",
      newPlan: "Жаңа жоспар",
      openReports: "Есептерді ашу",
      retry: "Қайталау",
      runMarketScan: "Нарық талдауын бастау",
      table: {
        date: "Күні",
        channel: "Арна",
        topic: "Тақырып",
        goal: "Мақсат",
        format: "Формат",
        cta: "Әрекетке шақыру",
        source: "Идея көзі",
        status: "Статус",
      },
      unknown: "Көрсетілмеген",
      untitled: "Тақырыпсыз",
    };
  }
  return {
    basedOn: "Источник данных",
    count: (count) => `Всего: ${count}`,
    createDraft: "Черновик",
    created: "Создан",
    creating: "Создаём",
    emptyTitle: "Контент-план пока не создан",
    emptyText:
      "Пока нет контент-плана. Создайте план на основе последнего анализа рынка.",
    goalPlaceholder:
      "Например: объяснить ценность услуги и получить заявки на консультацию",
    manualCreate: "Создать вручную",
    newPlan: "Новый план",
    openReports: "Открыть отчёты",
    retry: "Повторить",
    runMarketScan: "Запустить анализ рынка",
    table: {
      date: "Дата",
      channel: "Канал",
      topic: "Тема",
      goal: "Цель",
      format: "Формат",
      cta: "Призыв",
      source: "Источник идеи",
      status: "Статус",
    },
    unknown: "Не указан",
    untitled: "Без темы",
  };
}
