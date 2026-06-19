import { AppShell } from "@/components/app-shell";
import { ActiveContextProvider } from "@/lib/active-context-provider";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ActiveContextProvider>
      <AppShell>{children}</AppShell>
    </ActiveContextProvider>
  );
}
