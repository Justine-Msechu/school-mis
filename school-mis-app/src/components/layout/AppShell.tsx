import { useEffect } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useAuthStore } from "@/stores/authStore";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { refreshPermissions } = useAuthStore();

  // Re-fetch permissions from DB on every mount so role changes take effect
  // without requiring the user to manually log out and back in.
  useEffect(() => {
    refreshPermissions();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  );
}
