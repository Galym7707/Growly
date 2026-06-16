"use client";

import Link from "next/link";
import { Icon } from "@/components/icons";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { useLanguage } from "@/lib/i18n";

const capabilities = [
  ["Анализ рынка", "Собирает публичные источники и формирует проверяемый обзор."],
  [
    "Конкуренты",
    "Сравнивает предложения, призывы, сильные стороны и рыночные пробелы.",
  ],
  [
    "Контент-план",
    "Переводит рыночные наблюдения в темы, форматы и задачи на неделю.",
  ],
  [
    "Черновики",
    "Создаёт посты по брифу и сохраняет версии до согласования.",
  ],
  [
    "Отчёты",
    "Показывает выводы, таблицы, источники, риски и следующие действия.",
  ],
  [
    "Notion",
    "Синхронизирует отчёты, планы, источники и готовые материалы.",
  ],
];

const workflow = [
  "Укажите нишу и регион",
  "Проверьте собранные источники",
  "Получите конкурентный отчёт",
  "Сформируйте контент-план",
  "Подготовьте и согласуйте посты",
];

export default function LandingPage() {
  const { t } = useLanguage();

  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <nav aria-label="Навигация по странице">
          <a href="#product">{t("Возможности")}</a>
          <a href="#workflow">{t("Как работает")}</a>
          <a href="#cases">{t("Для кого")}</a>
        </nav>
        <LanguageSwitcher />
        <Link className="button button-dark button-small" href="/dashboard">
          {t("Открыть Growly")}
        </Link>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">{t("Маркетинговое рабочее пространство")}</p>
            <h1>{t("От рыночных данных до готового контента.")}</h1>
            <p className="hero-lead">
              {t(
                "Growly собирает публичные источники, готовит отчёты и помогает вести контент-процесс без разрыва между аналитикой и публикацией.",
              )}
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/dashboard">
                {t("Начать работу")}
                <Icon name="arrow" />
              </Link>
              <a className="text-link" href="#product">
                {t("Посмотреть возможности")}
                <Icon name="chevron" />
              </a>
            </div>
          </div>

          <div className="product-canvas" aria-label="Пример интерфейса Growly">
            <div className="canvas-sidebar">
              <span className="canvas-logo">G</span>
              <span className="canvas-line active" />
              <span className="canvas-line" />
              <span className="canvas-line short" />
              <span className="canvas-line" />
            </div>
            <div className="canvas-main">
              <div className="canvas-header">
                <div>
                  <span>{t("Рабочая область")}</span>
                  <strong>{t("Сегодня")}</strong>
                </div>
                <span className="canvas-status">{t("Система готова")}</span>
              </div>
              <div className="canvas-focus">
                <p>{t("Следующее действие")}</p>
                <h2>{t("Запустить анализ рынка")}</h2>
                <span>
                  {t(
                    "Укажите нишу и регион. Growly сохранит источники до начала анализа.",
                  )}
                </span>
                <div className="canvas-button">{t("Новый анализ")}</div>
              </div>
              <div className="canvas-grid">
                <div>
                  <span>{t("Последний отчёт")}</span>
                  <strong>{t("Ожидает данных")}</strong>
                  <small>{t("Появится после первого анализа")}</small>
                </div>
                <div>
                  <span>{t("Контент-план")}</span>
                  <strong>{t("Не создан")}</strong>
                  <small>{t("Формируется на основе источников")}</small>
                </div>
              </div>
              <div className="canvas-table">
                <div className="canvas-row canvas-row-head">
                  <span>{t("Задача")}</span>
                  <span>{t("Статус")}</span>
                  <span>{t("Данные")}</span>
                </div>
                <div className="canvas-row">
                  <span>{t("Анализ рынка")}</span>
                  <span>{t("Не запускался")}</span>
                  <span>{t("Нет")}</span>
                </div>
                <div className="canvas-row">
                  <span>{t("Синхронизация Notion")}</span>
                  <span>{t("По настройке")}</span>
                  <span>{t("Сервер")}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section capabilities" id="product">
          <div className="section-intro">
            <p className="eyebrow">{t("Что делает Growly")}</p>
            <h2>{t("Один процесс вместо набора разрозненных инструментов.")}</h2>
          </div>
          <div className="capability-list">
            {capabilities.map(([title, text], index) => (
              <article key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{t(title)}</h3>
                <p>{t(text)}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section workflow" id="workflow">
          <div className="workflow-copy">
            <p className="eyebrow">{t("Рабочий процесс")}</p>
            <h2>{t("Каждый вывод остаётся связан с источником.")}</h2>
            <p>
              {t(
                "Growly сначала сохраняет найденные материалы, затем анализирует их и только после этого формирует план и черновики.",
              )}
            </p>
          </div>
          <ol>
            {workflow.map((item, index) => (
              <li key={item}>
                <span>{index + 1}</span>
                <p>{t(item)}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section use-cases" id="cases">
          <div className="section-intro">
            <p className="eyebrow">{t("Для кого")}</p>
            <h2>{t("Для команд, которым нужен управляемый контент-процесс.")}</h2>
          </div>
          <div className="use-case-grid">
            <article>
              <h3>{t("Малый бизнес")}</h3>
              <p>{t("Понять рынок и регулярно готовить материалы без отдельного отдела.")}</p>
            </article>
            <article>
              <h3>{t("Маркетолог")}</h3>
              <p>{t("Собрать наблюдения, аргументы и план в одном рабочем пространстве.")}</p>
            </article>
            <article>
              <h3>{t("Агентство")}</h3>
              <p>{t("Вести исследование, согласование и отчётность по единой структуре.")}</p>
            </article>
            <article>
              <h3>{t("Telegram и Instagram")}</h3>
              <p>{t("Связать анализ предложений с практическими темами и черновиками.")}</p>
            </article>
          </div>
        </section>

        <section className="landing-cta">
          <div>
            <p className="eyebrow">Growly</p>
            <h2>{t("Начните с первого анализа рынка.")}</h2>
          </div>
          <Link className="button button-light" href="/market-scan">
            {t("Открыть рабочую область")}
            <Icon name="arrow" />
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <Logo />
        <p>{t("Аналитика, контент и согласование в одной системе.")}</p>
        <div className="landing-contact">
          <span>{t("Контакты")}</span>
          <a href="https://t.me/whoisnelya" rel="noreferrer" target="_blank">
            @whoisnelya
          </a>
        </div>
      </footer>
    </div>
  );
}
