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

type ActiveContextValue = {
  active: ActiveContext | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setActiveReport: (reportId: number) => Promise<ActiveContext | null>;
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

  const hydrateFromStorage = useCallback(async (): Promise<ActiveContext | null> => {
    const storedId = readStoredReportId();
    if (storedId === null) return null;
    try {
      const response = await apiRequest<{ report: unknown }>(
        `/reports/${storedId}`,
      );
      const next = buildActiveContextFromReport(
        (response as { report?: unknown }).report as never,
      );
      if (next) setActiveState(next);
      return next;
    } catch {
      return null;
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response =
        await apiRequest<ActiveContextResponse>("/context/active");
      const next = normalizeActiveContext(response);
      if (next) {
        setActive(next);
      } else {
        // Backend has no active context: fall back to the locally stored
        // report so the user's choice survives reloads.
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

  const setActiveReport = useCallback(
    async (reportId: number) => {
      const response = await apiRequest<ActiveContextResponse>(
        "/context/active",
        {
          method: "PATCH",
          body: JSON.stringify({ active_report_id: reportId }),
        },
      );
      const next = normalizeActiveContext(response);
      setActive(next);
      return next;
    },
    [setActive],
  );

  const clearActive = useCallback(async () => {
    try {
      await apiRequest("/context/active", {
        method: "PATCH",
        body: JSON.stringify({ active_report_id: null }),
      });
    } finally {
      setActive(null);
    }
  }, [setActive]);

  const value = useMemo(
    () => ({ active, loading, refresh, setActiveReport, clearActive }),
    [active, loading, refresh, setActiveReport, clearActive],
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
