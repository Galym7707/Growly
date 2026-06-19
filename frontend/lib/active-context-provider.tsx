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

export function ActiveContextProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [active, setActive] = useState<ActiveContext | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response =
        await apiRequest<ActiveContextResponse>("/context/active");
      setActive(normalizeActiveContext(response));
    } catch {
      setActive(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setActiveReport = useCallback(async (reportId: number) => {
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
  }, []);

  const clearActive = useCallback(async () => {
    await apiRequest("/context/active", {
      method: "PATCH",
      body: JSON.stringify({ active_report_id: null }),
    });
    setActive(null);
  }, []);

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
