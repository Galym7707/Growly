"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiRequest } from "@/lib/api";

export type WorkspaceRole = "owner" | "admin" | "editor" | "viewer";

export type WorkspacePermissions = {
  can_view: boolean;
  can_edit: boolean;
  can_publish: boolean;
  can_manage_team: boolean;
  can_manage_integrations: boolean;
};

export type CurrentWorkspace = {
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  permissions: WorkspacePermissions;
};

type WorkspaceContextValue = {
  workspace: CurrentWorkspace | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspace, setWorkspace] = useState<CurrentWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setWorkspace(await apiRequest<CurrentWorkspace>("/workspaces/current"));
    } catch (value) {
      setError(value instanceof Error ? value.message : "Unknown error");
      setWorkspace(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <WorkspaceContext.Provider value={{ workspace, loading, error, refresh }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (value === null) {
    return {
      workspace: null,
      loading: false,
      error: "",
      refresh: async () => {},
    };
  }
  return value;
}

export const ROLE_LABELS: Record<WorkspaceRole, string> = {
  owner: "Владелец",
  admin: "Администратор",
  editor: "Редактор",
  viewer: "Только просмотр",
};
