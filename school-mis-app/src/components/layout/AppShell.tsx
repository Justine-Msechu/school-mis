import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import SubscriptionBanner from "./SubscriptionBanner";
import { useAuthStore } from "@/stores/authStore";
import "@/stores/themeStore"; // ensure theme is applied on load

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { refreshPermissions } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    refreshPermissions();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        <SubscriptionBanner />
        <main className="flex-1 overflow-y-auto" style={{ backgroundColor: "var(--color-surface-2)" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
