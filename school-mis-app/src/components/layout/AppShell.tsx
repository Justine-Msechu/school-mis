import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import SubscriptionBanner from "./SubscriptionBanner";
import SubscriptionLockScreen from "./SubscriptionLockScreen";
import PlanUpgradeOverlay from "./PlanUpgradeOverlay";
import ImpersonationBanner from "./ImpersonationBanner";
import AiChat from "@/components/ai/AiChat";
import { useAuthStore } from "@/stores/authStore";
import { useSubscriptionStore } from "@/stores/subscriptionStore";
import { useImpersonationStore } from "@/stores/impersonationStore";
import "@/stores/themeStore"; // ensure theme is applied on load

interface PlanRestriction {
  message: string;
  current_plan: string;
  required_plan: string;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { refreshPermissions } = useAuthStore();
  const fetchPlan = useSubscriptionStore((s) => s.fetch);
  const { active: isImpersonating } = useImpersonationStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [locked, setLocked] = useState(false);
  const [planRestriction, setPlanRestriction] = useState<PlanRestriction | null>(null);

  useEffect(() => {
    refreshPermissions();
    fetchPlan();
  }, []);

  useEffect(() => {
    const onExpired = () => setLocked(true);
    const onRestricted = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setPlanRestriction({
        message:       detail.message      ?? "This feature is not available on your plan.",
        current_plan:  detail.current_plan ?? "basic",
        required_plan: detail.required_plan ?? "standard",
      });
    };
    window.addEventListener("subscription:expired", onExpired);
    window.addEventListener("plan:restricted", onRestricted);
    return () => {
      window.removeEventListener("subscription:expired", onExpired);
      window.removeEventListener("plan:restricted", onRestricted);
    };
  }, []);

  // Clear plan restriction overlay whenever the route changes
  useEffect(() => {
    setPlanRestriction(null);
  }, [children]);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {locked && <SubscriptionLockScreen onUnlocked={() => setLocked(false)} />}
      {isImpersonating && <ImpersonationBanner />}
      <div className="flex flex-1 min-h-0 overflow-hidden">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        <SubscriptionBanner />
        <main className="flex-1 overflow-y-auto relative" style={{ backgroundColor: "var(--color-surface-2)" }}>
          {children}
          {planRestriction && (
            <PlanUpgradeOverlay
              currentPlan={planRestriction.current_plan}
              requiredPlan={planRestriction.required_plan}
              message={planRestriction.message}
              onDismiss={() => setPlanRestriction(null)}
            />
          )}
        </main>
      </div>
      <AiChat />
      </div>
    </div>
  );
}
