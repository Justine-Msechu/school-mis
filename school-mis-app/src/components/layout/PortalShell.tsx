import { useState } from "react";
import { LogOut, GraduationCap, Menu, X } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { logout as apiLogout } from "@/api/auth";
import NotificationBell from "@/components/layout/NotificationBell";

const ROLE_LABEL: Record<string, string> = {
  student_portal: "Student Portal",
  parent_portal:  "Parent Portal",
};

interface Props {
  children: React.ReactNode;
}

export default function PortalShell({ children }: Props) {
  const { user, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    try { await apiLogout(); } catch { /* ignore */ }
    logout();
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--color-bg)" }}>
      {/* Top bar */}
      <header
        className="flex items-center justify-between px-4 h-14 border-b shadow-sm"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
            <GraduationCap size={15} className="text-white" />
          </div>
          <span className="font-semibold text-sm" style={{ color: "var(--color-on-surface)" }}>
            {ROLE_LABEL[user?.role ?? ""] ?? "Portal"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <NotificationBell />
          <div className="hidden sm:flex items-center gap-3">
            <span className="text-sm" style={{ color: "var(--color-on-surface-muted)" }}>
              {user?.full_name}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors hover:bg-red-50 hover:text-red-600 hover:border-red-200"
              style={{ color: "var(--color-on-surface-muted)", borderColor: "var(--color-border)" }}
            >
              <LogOut size={14} /> Sign out
            </button>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="sm:hidden p-1.5 rounded-lg"
            style={{ color: "var(--color-on-surface-muted)" }}
            onClick={() => setMenuOpen(o => !o)}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div
          className="sm:hidden border-b px-4 py-3 flex flex-col gap-2"
          style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
        >
          <span className="text-sm font-medium" style={{ color: "var(--color-on-surface)" }}>
            {user?.full_name}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-red-600 py-1"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      )}

      {/* Page content */}
      <main className="flex-1 overflow-auto p-4 sm:p-6 max-w-4xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
