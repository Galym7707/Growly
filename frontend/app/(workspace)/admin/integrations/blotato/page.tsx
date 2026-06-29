"use client";

import { useCallback, useEffect, useState } from "react";
import { LoadingState, PageHeader, Status } from "@/components/ui";
import { ApiError, apiRequest, formatDate, formatStatusLabel } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type {
  BlotatoAccount,
  SocialConnectionRequestInfo,
} from "@/lib/integrations";

type BlotatoConfigStatus = {
  api_key_configured: boolean;
  base_url?: string;
  connected: boolean;
  accounts_count: number;
  last_checked_at: string | null;
};

export default function AdminBlotatoPage() {
  const { locale, t } = useLanguage();
  const [denied, setDenied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<BlotatoConfigStatus | null>(null);
  const [requests, setRequests] = useState<SocialConnectionRequestInfo[]>([]);
  const [accounts, setAccounts] = useState<BlotatoAccount[]>([]);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeKind, setNoticeKind] = useState<"success" | "error">("success");
  const [linkChoice, setLinkChoice] = useState<Record<number, string>>({});

  function flash(message: string, kind: "success" | "error" = "success") {
    setNotice(message);
    setNoticeKind(kind);
  }

  function failureMessage(value: unknown): string {
    return value instanceof Error ? t(value.message) : t("Неизвестная ошибка");
  }

  const load = useCallback(async () => {
    setLoading(true);
    setDenied(false);
    try {
      const [statusResp, requestsResp] = await Promise.all([
        apiRequest<BlotatoConfigStatus>("/admin/blotato/status"),
        apiRequest<{ requests: SocialConnectionRequestInfo[] }>(
          "/admin/social-connection-requests",
        ),
      ]);
      setStatus(statusResp);
      setRequests(requestsResp.requests || []);
    } catch (value) {
      if (value instanceof ApiError && value.status === 403) {
        setDenied(true);
      } else {
        flash(failureMessage(value), "error");
      }
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function refreshAccounts() {
    setBusy("accounts");
    setNotice("");
    try {
      const resp = await apiRequest<{ accounts: BlotatoAccount[] }>(
        "/admin/blotato/accounts",
      );
      setAccounts(resp.accounts || []);
      flash(t("Список аккаунтов обновлён."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function checkStatus() {
    setBusy("status");
    setNotice("");
    try {
      const resp = await apiRequest<BlotatoConfigStatus>("/admin/blotato/status");
      setStatus(resp);
      flash(resp.connected ? t("Blotato подключён") : t("Blotato не отвечает"), resp.connected ? "success" : "error");
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function setRequestStatus(id: number, status: string) {
    setBusy(`req-${id}`);
    setNotice("");
    try {
      await apiRequest(`/admin/social-connection-requests/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      await load();
      flash(t("Статус заявки обновлён."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  async function linkToRequest(requestId: number) {
    const accountId = linkChoice[requestId];
    if (!accountId) {
      flash(t("Сначала выберите аккаунт Blotato."), "error");
      return;
    }
    setBusy(`link-${requestId}`);
    setNotice("");
    try {
      await apiRequest("/admin/social-accounts/link", {
        method: "POST",
        body: JSON.stringify({
          external_account_id: accountId,
          request_id: requestId,
        }),
      });
      await load();
      flash(t("Аккаунт связан с заявкой."));
    } catch (value) {
      flash(failureMessage(value), "error");
    } finally {
      setBusy("");
    }
  }

  if (loading) {
    return (
      <div className="workspace-page">
        <LoadingState />
      </div>
    );
  }

  if (denied) {
    return (
      <div className="workspace-page">
        <PageHeader
          eyebrow={t("Администрирование")}
          title={t("Доступ ограничен")}
        />
        <div className="feedback feedback-error">
          {t("Доступ только для администратора Growly.")}
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow={t("Администрирование")}
        title={t("Blotato и подключения")}
        description={t("Подключение клиентов к автопостингу выполняется вручную через официальный OAuth.")}
      />

      {notice ? (
        <div className={`feedback feedback-${noticeKind === "error" ? "error" : "success"}`}>
          {notice}
        </div>
      ) : null}

      {/* Safety instructions */}
      <section className="form-panel">
        <h2>{t("Как подключать клиента безопасно")}</h2>
        <ol className="setup-checklist">
          <li><span className="setup-step-index">1</span>{t("Никогда не просите пароль от Instagram.")}</li>
          <li><span className="setup-step-index">2</span>{t("Подключение должно проходить через официальный OAuth.")}</li>
          <li><span className="setup-step-index">3</span>{t("Клиент сам входит в Instagram/Meta на своём устройстве.")}</li>
          <li><span className="setup-step-index">4</span>{t("После подключения нажмите «Обновить аккаунты» в Growly.")}</li>
          <li><span className="setup-step-index">5</span>{t("Найдите новый accountId из Blotato и свяжите его с заявкой клиента.")}</li>
        </ol>
        <p className="feedback feedback-warning">
          {t("Не подключайте аккаунт клиента, если вы не уверены, что клиент сам дал разрешение через OAuth.")}
        </p>
      </section>

      {/* Block 1: Blotato status */}
      <section className="integration-card integration-card-wide">
        <div className="integration-card-head">
          <h2>{t("Статус Blotato")}</h2>
          <Status value={status?.connected ? "active" : "disabled"}>
            {status?.connected ? t("Подключено") : t("Не подключено")}
          </Status>
        </div>
        <ul className="integration-facts">
          <li>
            BLOTATO_API_KEY:{" "}
            <strong>{status?.api_key_configured ? t("настроен") : t("не настроен")}</strong>
          </li>
          <li>
            {t("Аккаунтов в Blotato")}: <strong>{status?.accounts_count ?? 0}</strong>
          </li>
          {status?.last_checked_at ? (
            <li>
              {t("Последняя проверка")}: <strong>{formatDate(status.last_checked_at, locale)}</strong>
            </li>
          ) : null}
        </ul>
        <div className="integration-actions">
          <button className="button button-secondary" disabled={busy !== ""} onClick={checkStatus} type="button">
            {busy === "status" ? t("Проверяем") : t("Проверить подключение")}
          </button>
          <button className="button button-secondary" disabled={busy !== ""} onClick={refreshAccounts} type="button">
            {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
          </button>
        </div>
      </section>

      {/* Block 2: connection requests */}
      <section className="workspace-section">
        <div className="section-heading">
          <h2>{t("Заявки на подключение")}</h2>
        </div>
        {requests.length === 0 ? (
          <p className="plan-note plan-note-muted">{t("Заявок пока нет.")}</p>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>{t("Пользователь")}</th>
                  <th>{t("Имя пользователя Instagram")}</th>
                  <th>{t("Статус")}</th>
                  <th>{t("Дата")}</th>
                  <th>{t("Действия")}</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.id}</td>
                    <td>{request.user_email || request.workspace_id || "—"}</td>
                    <td>{request.requested_username || "—"}</td>
                    <td>
                      <Status value={request.status}>
                        {formatStatusLabel(request.status, locale)}
                      </Status>
                    </td>
                    <td>{formatDate(request.created_at, locale)}</td>
                    <td>
                      <div className="plan-row-actions">
                        <button
                          className="button button-secondary button-small"
                          disabled={busy !== "" || request.status === "connected"}
                          onClick={() => setRequestStatus(request.id, "in_progress")}
                          type="button"
                        >
                          {t("В работу")}
                        </button>
                        <select
                          onChange={(event) =>
                            setLinkChoice((current) => ({
                              ...current,
                              [request.id]: event.target.value,
                            }))
                          }
                          value={linkChoice[request.id] || ""}
                        >
                          <option value="">{t("Выберите аккаунт")}</option>
                          {accounts.map((account) => (
                            <option key={account.id} value={account.id}>
                              {(account.platform || "?") + ": "}
                              {account.display_name || account.name || account.id}
                            </option>
                          ))}
                        </select>
                        <button
                          className="button button-primary button-small"
                          disabled={busy !== ""}
                          onClick={() => linkToRequest(request.id)}
                          type="button"
                        >
                          {t("Связать аккаунт")}
                        </button>
                        <button
                          className="button button-secondary button-small"
                          disabled={busy !== ""}
                          onClick={() => setRequestStatus(request.id, "failed")}
                          type="button"
                        >
                          {t("Отметить ошибку")}
                        </button>
                        <button
                          className="button button-secondary button-small"
                          disabled={busy !== ""}
                          onClick={() => setRequestStatus(request.id, "cancelled")}
                          type="button"
                        >
                          {t("Отменить")}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Block 3: Blotato accounts */}
      <section className="workspace-section">
        <div className="section-heading">
          <h2>{t("Аккаунты из Blotato")}</h2>
          <button className="button button-secondary button-small" disabled={busy !== ""} onClick={refreshAccounts} type="button">
            {busy === "accounts" ? t("Обновляем") : t("Обновить аккаунты")}
          </button>
        </div>
        {accounts.length === 0 ? (
          <p className="plan-note plan-note-muted">
            {t("Нажмите «Обновить аккаунты», чтобы получить список из Blotato.")}
          </p>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("Платформа")}</th>
                  <th>{t("Аккаунт")}</th>
                  <th>external_account_id</th>
                  <th>{t("Связан с")}</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>{account.platform || "—"}</td>
                    <td>{account.display_name || account.name || "—"}</td>
                    <td>{account.id}</td>
                    <td>{account.linked_workspace_id || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
