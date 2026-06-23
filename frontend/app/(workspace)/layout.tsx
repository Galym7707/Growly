import { AppShell } from "@/components/app-shell";
import { ActiveContextProvider } from "@/lib/active-context-provider";
import { WorkspaceProvider } from "@/lib/workspace";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WorkspaceProvider>
      <ActiveContextProvider>
        <AppShell>{children}</AppShell>
      </ActiveContextProvider>
    </WorkspaceProvider>
  );
}
