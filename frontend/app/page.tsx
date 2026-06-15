import Link from "next/link";
import { Icon } from "@/components/icons";
import { Logo } from "@/components/logo";

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
  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <nav aria-label="Навигация по странице">
          <a href="#product">Возможности</a>
          <a href="#workflow">Как работает</a>
          <a href="#cases">Для кого</a>
        </nav>
        <Link className="button button-dark button-small" href="/dashboard">
          Открыть Growly
        </Link>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Маркетинговое рабочее пространство</p>
            <h1>От рыночных данных до готового контента.</h1>
            <p className="hero-lead">
              Growly собирает публичные источники, готовит отчёты и помогает
              вести контент-процесс без разрыва между аналитикой и публикацией.
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/dashboard">
                Начать работу
                <Icon name="arrow" />
              </Link>
              <a className="text-link" href="#product">
                Посмотреть возможности
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
                  <span>Рабочая область</span>
                  <strong>Сегодня</strong>
                </div>
                <span className="canvas-status">Система готова</span>
              </div>
              <div className="canvas-focus">
                <p>Следующее действие</p>
                <h2>Запустить анализ рынка</h2>
                <span>
                  Укажите нишу и регион. Growly сохранит источники до начала
                  анализа.
                </span>
                <div className="canvas-button">Новый анализ</div>
              </div>
              <div className="canvas-grid">
                <div>
                  <span>Последний отчёт</span>
                  <strong>Ожидает данных</strong>
                  <small>Появится после первого анализа</small>
                </div>
                <div>
                  <span>Контент-план</span>
                  <strong>Не создан</strong>
                  <small>Формируется на основе источников</small>
                </div>
              </div>
              <div className="canvas-table">
                <div className="canvas-row canvas-row-head">
                  <span>Задача</span>
                  <span>Статус</span>
                  <span>Данные</span>
                </div>
                <div className="canvas-row">
                  <span>Анализ рынка</span>
                  <span>Не запускался</span>
                  <span>Нет</span>
                </div>
                <div className="canvas-row">
                  <span>Синхронизация Notion</span>
                  <span>По настройке</span>
                  <span>Сервер</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section capabilities" id="product">
          <div className="section-intro">
            <p className="eyebrow">Что делает Growly</p>
            <h2>Один процесс вместо набора разрозненных инструментов.</h2>
          </div>
          <div className="capability-list">
            {capabilities.map(([title, text], index) => (
              <article key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section workflow" id="workflow">
          <div className="workflow-copy">
            <p className="eyebrow">Рабочий процесс</p>
            <h2>Каждый вывод остаётся связан с источником.</h2>
            <p>
              Growly сначала сохраняет найденные материалы, затем анализирует их
              и только после этого формирует план и черновики.
            </p>
          </div>
          <ol>
            {workflow.map((item, index) => (
              <li key={item}>
                <span>{index + 1}</span>
                <p>{item}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section use-cases" id="cases">
          <div className="section-intro">
            <p className="eyebrow">Для кого</p>
            <h2>Для команд, которым нужен управляемый контент-процесс.</h2>
          </div>
          <div className="use-case-grid">
            <article>
              <h3>Малый бизнес</h3>
              <p>Понять рынок и регулярно готовить материалы без отдельного отдела.</p>
            </article>
            <article>
              <h3>Маркетолог</h3>
              <p>Собрать наблюдения, аргументы и план в одном рабочем пространстве.</p>
            </article>
            <article>
              <h3>Агентство</h3>
              <p>Вести исследование, согласование и отчётность по единой структуре.</p>
            </article>
            <article>
              <h3>Telegram и Instagram</h3>
              <p>Связать анализ предложений с практическими темами и черновиками.</p>
            </article>
          </div>
        </section>

        <section className="landing-cta">
          <div>
            <p className="eyebrow">Growly</p>
            <h2>Начните с первого анализа рынка.</h2>
          </div>
          <Link className="button button-light" href="/market-scan">
            Открыть рабочую область
            <Icon name="arrow" />
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <Logo />
        <p>Аналитика, контент и согласование в одной системе.</p>
        <span>Growly</span>
      </footer>
    </div>
  );
}
