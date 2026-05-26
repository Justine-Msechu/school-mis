import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import SubscriptionBanner from "./SubscriptionBanner";
import SubscriptionLockScreen from "./SubscriptionLockScreen";
import { useAuthStore } from "@/stores/authStore";
import "@/stores/themeStore"; // ensure theme is applied on load

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { refreshPermissions } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    refreshPermissions();
  }, []);

  useEffect(() => {
    const handler = () => setLocked(true);
    window.addEventListener("subscription:expired", handler);
    return () => window.removeEventListener("subscription:expired", handler);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {locked && <SubscriptionLockScreen onUnlocked={() => setLocked(false)} />}
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
