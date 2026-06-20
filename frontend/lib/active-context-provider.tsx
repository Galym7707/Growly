"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiRequest } from "@/lib/api";
import {
  ACTIVE_REPORT_STORAGE_KEY,
  buildActiveContextFromReport,
  normalizeActiveContext,
  type ActiveContext,
  type ActiveContextResponse,
} from "@/lib/active-context";
import type { Report } from "@/lib/types";

type ActiveContextValue = {
  active: ActiveContext | null;
  loading: boolean;
  refresh: () => Promise<void>;
  /** Select a report we already have in memory — updates the UI synchronously. */
  applyReport: (report: Report) => ActiveContext | null;
  /** Hydrate the active report from its id (URL param / reload) via the API. */
  loadActiveReport: (reportId: number) => Promise<ActiveContext | null>;
  clearActive: () => Promise<void>;
};

const ActiveWorkspaceContext = createContext<ActiveContextValue | null>(null);

function readStoredReportId(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(ACTIVE_REPORT_STORAGE_KEY);
    return raw && /^\d+$/.test(raw) ? Number(raw) : null;
  } catch {
    return null;
  }
}

function writeStoredReportId(reportId: number | null): void {
  if (typeof window === "undefined") return;
  try {
    if (reportId === null) {
      window.localStorage.removeItem(ACTIVE_REPORT_STORAGE_KEY);
    } else {
      window.localStorage.setItem(ACTIVE_REPORT_STORAGE_KEY, String(reportId));
    }
  } catch {
    // Ignore storage failures (private mode, quota, etc.).
  }
}

export function ActiveContextProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [active, setActiveState] = useState<ActiveContext | null>(null);
  const [loading, setLoading] = useState(true);

  const setActive = useCallback((next: ActiveContext | null) => {
    setActiveState(next);
    writeStoredReportId(next ? next.report_id : null);
  }, []);

  // Persist the choice server-side without blocking the UI. A failure here
  // (e.g. backend not yet deployed) must never stop the user from continuing —
  // the local state and localStorage already carry the selection.
  const persist = useCallback((reportId: number) => {
    void apiRequest("/context/active", {
      method: "PATCH",
      body: JSON.stringify({ active_report_id: reportId }),
    }).catch(() => {});
  }, []);

  const applyReport = useCallback(
    (report: Report) => {
      const next = buildActiveContextFromReport(report);
      if (!next) return null;
      setActive(next);
      persist(next.report_id);
      return next;
    },
    [persist, setActive],
  );

  const loadActiveReport = useCallback(
    async (reportId: number) => {
      try {
        const response = await apiRequest<{ report: unknown }>(
          `/reports/${reportId}`,
        );
        const next = buildActiveContextFromReport(
          (response as { report?: unknown }).report as never,
        );
        if (next) {
          setActive(next);
          persist(next.report_id);
        }
        return next;
      } catch {
        return null;
      }
    },
    [persist, setActive],
  );

  const hydrateFromStorage = useCallback(async (): Promise<ActiveContext | null> => {
    const storedId = readStoredReportId();
    if (storedId === null) return null;
    return loadActiveReport(storedId);
  }, [loadActiveReport]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response =
        await apiRequest<ActiveContextResponse>("/context/active");
      const next = normalizeActiveContext(response);
      if (next) {
        setActive(next);
      } else {
        await hydrateFromStorage();
      }
    } catch {
      await hydrateFromStorage();
    } finally {
      setLoading(false);
    }
  }, [hydrateFromStorage, setActive]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const clearActive = useCallback(async () => {
    setActive(null);
    void apiRequest("/context/active", {
      method: "PATCH",
      body: JSON.stringify({ active_report_id: null }),
    }).catch(() => {});
  }, [setActive]);

  const value = useMemo(
    () => ({ active, loading, refresh, applyReport, loadActiveReport, clearActive }),
    [active, loading, refresh, applyReport, loadActiveReport, clearActive],
  );

  return (
    <ActiveWorkspaceContext.Provider value={value}>
      {children}
    </ActiveWorkspaceContext.Provider>
  );
}

export function useActiveContext(): ActiveContextValue {
  const value = useContext(ActiveWorkspaceContext);
  if (!value) {
    throw new Error("useActiveContext requires ActiveContextProvider");
  }
  return value;
}
