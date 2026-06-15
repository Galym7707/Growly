"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  asCompetitors,
  asMetricRows,
  asStrings,
} from "@/lib/report-data";
import type { Report } from "@/lib/types";

export function ReportView({ report }: { report: Report }) {
  const structure = report.structure || {};
  const competitorRows = asCompetitors(structure.competitors);
  const chartRows = asMetricRows(
    structure.publication_metrics || structure.metrics || structure.posts,
  );
  const sections = [
    ["Повторяющиеся предложения", structure.repeating_offers],
    ["Призывы к действию", structure.repeating_ctas],
    ["Пробелы в контенте", structure.content_gaps],
    ["Боли аудитории", structure.audience_pains],
    ["Рекомендуемое позиционирование", structure.recommended_positioning],
    ["Действия на неделю", structure.actions_this_week],
    ["Идеи контента", structure.content_ideas],
    ["Риски и ограничения", structure.limitations || structure.risks],
  ] as const;
  const hasStructuredContent =
    competitorRows.length > 0 ||
    chartRows.length > 0 ||
    sections.some(([, value]) => asStrings(value).length > 0);

  return (
    <>
      {report.summary ? (
        <section className="report-summary">
          <p className="eyebrow">Главный вывод</p>
          <h2>{report.summary}</h2>
        </section>
      ) : null}

      {competitorRows.length ? (
        <section className="report-section">
          <h2>Сравнение конкурентов</h2>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Конкурент</th>
                  <th>Канал</th>
                  <th>Предложение</th>
                  <th>Цена / ценность</th>
                  <th>Призыв</th>
                  <th>Сильная сторона</th>
                  <th>Слабая сторона</th>
                  <th>Возможность</th>
                </tr>
              </thead>
              <tbody>
                {competitorRows.map((row, index) => (
                  <tr key={`${row.competitor || "competitor"}-${index}`}>
                    <td>{row.competitor || "Не подтверждено"}</td>
                    <td>{row.channel || "Не подтверждено"}</td>
                    <td>{row.offer || "Не подтверждено"}</td>
                    <td>{row.price_value || "Не подтверждено"}</td>
                    <td>{row.cta || "Не подтверждено"}</td>
                    <td>{row.strengths || "Не подтверждено"}</td>
                    <td>{row.weaknesses || "Не подтверждено"}</td>
                    <td>{row.opportunity || "Требуется больше данных"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {chartRows.length ? (
        <section className="report-section">
          <h2>Динамика публикаций</h2>
          <div className="metric-chart">
            <ResponsiveContainer height="100%" width="100%">
              <LineChart data={chartRows}>
                <CartesianGrid stroke="#e6e3dc" strokeDasharray="3 3" />
                <XAxis dataKey="title" stroke="#77776f" />
                <YAxis stroke="#77776f" />
                <Tooltip />
                <Line
                  dataKey="views"
                  dot={false}
                  stroke="#1f6f50"
                  strokeWidth={2}
                  type="monotone"
                />
                <Line
                  dataKey="reactions"
                  dot={false}
                  stroke="#9b671b"
                  strokeWidth={2}
                  type="monotone"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      ) : null}

      {sections.map(([title, value]) => {
        const values = asStrings(value);
        return values.length ? (
          <section className="report-section" key={title}>
            <h2>{title}</h2>
            <ul>
              {values.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null;
      })}

      {report.evidence.length ? (
        <section className="report-section">
          <h2>Источники</h2>
          <ul>
            {report.evidence.map((value, index) => {
              const href =
                typeof value === "string"
                  ? value
                  : typeof value === "object" &&
                      value &&
                      "url" in value
                    ? String(value.url)
                    : "";
              return (
                <li key={`${href}-${index}`}>
                  {href ? (
                    <a href={href} rel="noreferrer" target="_blank">
                      {href}
                    </a>
                  ) : (
                    String(value)
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {report.body && !hasStructuredContent ? (
        <section className="report-section">
          <h2>Полный текст</h2>
          <div className="report-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.body}
            </ReactMarkdown>
          </div>
        </section>
      ) : null}
    </>
  );
}
