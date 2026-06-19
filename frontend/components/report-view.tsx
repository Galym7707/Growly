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
import { asCompetitors, asMetricRows } from "@/lib/report-data";
import { reportSections, shortConclusion } from "@/lib/report-sections";
import type { Report } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export function ReportView({ report }: { report: Report }) {
  const { t } = useLanguage();
  const structure = report.structure || {};
  const competitorRows = asCompetitors(structure.competitors);
  const chartRows = asMetricRows(
    structure.publication_metrics || structure.metrics || structure.posts,
  );
  const sections = reportSections(structure);
  const conclusion = shortConclusion(report.summary, 5);
  const evidence = report.evidence || [];
  const hasStructuredContent =
    competitorRows.length > 0 ||
    chartRows.length > 0 ||
    sections.length > 0 ||
    evidence.length > 0;

  return (
    <>
      {conclusion ? (
        <section className="report-summary">
          <p className="eyebrow">{t("Главный вывод")}</p>
          <h2>{conclusion}</h2>
        </section>
      ) : null}

      {competitorRows.length ? (
        <section className="report-section report-card">
          <h2>{t("Конкуренты / источники")}</h2>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("Конкурент")}</th>
                  <th>{t("Канал")}</th>
                  <th>{t("Предложение")}</th>
                  <th>{t("Цена / ценность")}</th>
                  <th>{t("Призыв")}</th>
                  <th>{t("Сильная сторона")}</th>
                  <th>{t("Слабая сторона")}</th>
                  <th>{t("Возможность")}</th>
                </tr>
              </thead>
              <tbody>
                {competitorRows.map((row, index) => (
                  <tr key={`${row.competitor || "competitor"}-${index}`}>
                    <td>{row.competitor || t("Не подтверждено")}</td>
                    <td>{row.channel || t("Не подтверждено")}</td>
                    <td>{row.offer || t("Не подтверждено")}</td>
                    <td>{row.price_value || t("Не подтверждено")}</td>
                    <td>{row.cta || t("Не подтверждено")}</td>
                    <td>{row.strengths || t("Не подтверждено")}</td>
                    <td>{row.weaknesses || t("Не подтверждено")}</td>
                    <td>{row.opportunity || t("Требуется больше данных")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {chartRows.length ? (
        <section className="report-section report-card">
          <h2>{t("Динамика публикаций")}</h2>
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

      {sections.map((section) => (
        <section className="report-section report-card" key={section.key}>
          <h2>{t(section.title)}</h2>
          <ul>
            {section.items.map((item, index) => (
              <li key={`${section.key}-${index}`}>{item}</li>
            ))}
          </ul>
        </section>
      ))}

      {evidence.length ? (
        <section className="report-section report-card">
          <h2>{t("Источники")}</h2>
          <ul>
            {evidence.map((value, index) => {
              const href =
                typeof value === "string"
                  ? value
                  : typeof value === "object" && value && "url" in value
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
        <section className="report-section report-card">
          <h2>{t("Полный текст")}</h2>
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
