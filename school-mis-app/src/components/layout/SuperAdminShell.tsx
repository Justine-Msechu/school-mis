import { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clsx } from "clsx";
import {
  LayoutDashboard, Building2, Shield, Settings,
  LogOut, BookOpen, X, Menu, Palette, Layers, Megaphone, Bug, Bell, Images, KeyRound,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore, THEMES } from "@/stores/themeStore";
import { logout } from "@/api/auth";
import { getAlertCount, type AlertCount } from "@/api/healthMonitor";
import "@/stores/themeStore";

const NAV = [
  { icon: LayoutDashboard, label: "Dashboard",       to: "/platform" },
  { icon: Building2,       label: "Schools",         to: "/platform/schools" },
  { icon: Layers,          label: "Module Access",   to: "/platform/features" },
  { icon: Megaphone,       label: "Announcements",   to: "/platform/announcements" },
  { icon: Images,          label: "Landing Media",   to: "/platform/media" },
  { icon: KeyRound,        label: "Roles & Access",  to: "/platform/rbac" },
  { icon: Shield,          label: "Audit Log",       to: "/platform/audit" },
  { icon: Bug,             label: "Error Logs",      to: "/platform/errors" },
  { icon: Settings,        label: "Settings",        to: "/platform/settings" },
];

function PlatformSidebar({ onClose }: { onClose: () => void }) {
  const { user, logout: storeLogout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); } catch { /* ignore */ }
    storeLogout();
    navigate("/login");
  };

  const initials = user?.full_name
    ?.split(" ").slice(0, 2).map(n => n[0]).join("").toUpperCase() ?? "SA";

  return (
    <aside className="flex flex-col w-[220px] h-full bg-sidebar-bg">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-red-600 flex items-center justify-center">
            <BookOpen size={15} className="text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold text-white leading-tight truncate">Platform Admin</p>
            <p className="text-2xs text-sidebar-text">YouthTech</p>
          </div>
          <button onClick={onClose} className="md:hidden p-1 rounded text-sidebar-text hover:text-white">
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-0.5">
        {NAV.map(({ icon: Icon, label, to }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/platform"}
            onClick={onClose}
            className={({ isActive }) => clsx(
              "flex items-center gap-2.5 px-3 h-9 rounded-lg text-sm transition-colors relative",
              isActive
                ? "bg-white/14 text-white font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-5 before:w-0.5 before:bg-red-400 before:rounded-full"
                : "text-sidebar-text hover:bg-white/8 hover:text-gray-200",
            )}
          >
            <Icon size={16} className="flex-shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User strip */}
      <div className="px-2 pb-3">
        <div className="border border-sidebar-border rounded-xl p-3 bg-sidebar-border/40">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-xs font-bold text-white">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
              <p className="text-2xs text-red-400">Platform Admin</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-2xs text-sidebar-text hover:text-red-400 transition-colors"
          >
            <LogOut size={12} /> Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}

function PlatformTopbar({ onMenuClick }: { onMenuClick: () => void }) {
  const navigate              = useNavigate();
  const { theme, setTheme }   = useThemeStore();
  const [themeOpen, setThemeOpen] = useState(false);
  const [alerts, setAlerts]   = useState<AlertCount>({ total: 0, critical: 0 });

  useEffect(() => {
    const fetch = () => getAlertCount().then(setAlerts).catch(() => {});
    fetch();
    const id = setInterval(fetch, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      className="h-14 flex items-center px-4 md:px-6 flex-shrink-0 gap-3 border-b"
      style={{ background: "var(--color-topbar-bg)", borderColor: "var(--color-topbar-border)" }}
    >
      <button onClick={onMenuClick} className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
        <Menu size={20} />
      </button>

      <div className="flex-1">
        <p className="text-sm font-semibold" style={{ color: "var(--color-on-surface)" }}>
          Platform Management Console
        </p>
        <p className="text-xs" style={{ color: "var(--color-on-surface-muted)" }}>
          Full system ownership
        </p>
      </div>

      {/* Health alert bell */}
      <button
        onClick={() => navigate("/platform")}
        className="relative p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        style={{ color: alerts.critical > 0 ? "#DC2626" : alerts.total > 0 ? "#D97706" : "var(--color-on-surface-muted)" }}
        title={alerts.total > 0 ? `${alerts.total} active alert${alerts.total !== 1 ? "s" : ""}` : "System healthy"}
      >
        <Bell size={17} />
        {alerts.critical > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-0.5">
            {alerts.critical > 9 ? "9+" : alerts.critical}
          </span>
        )}
        {alerts.critical === 0 && alerts.total > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-amber-400 rounded-full border-2 border-white" />
        )}
      </button>

      {/* Theme switcher */}
      <div className="relative">
        <button
          onClick={() => setThemeOpen(o => !o)}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          style={{ color: "var(--color-on-surface-muted)" }}
        >
          <Palette size={17} />
        </button>
        {themeOpen && (
          <div
            className="absolute right-0 top-full mt-1.5 rounded-xl shadow-lg border py-1 z-50 min-w-[140px]"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            {THEMES.map(t => (
              <button
                key={t.key}
                onClick={() => { setTheme(t.key); setThemeOpen(false); }}
                className="flex items-center gap-2.5 w-full px-3 py-2 text-sm transition-colors"
                style={{
                  color: theme === t.key ? "var(--color-accent)" : "var(--color-on-surface)",
                  backgroundColor: theme === t.key ? "var(--color-accent-light)" : "transparent",
                }}
              >
                {t.label}
                {theme === t.key && <span className="ml-auto text-xs">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

export default function SuperAdminShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sidebarContent = <PlatformSidebar onClose={() => setSidebarOpen(false)} />;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex flex-shrink-0 min-h-screen">
        {sidebarContent}
      </div>

      {/* Mobile drawer */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <div className="relative flex-shrink-0">{sidebarContent}</div>
        </div>
      )}

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <PlatformTopbar onMenuClick={() => setSidebarOpen(true)} />
        <main
          className="flex-1 overflow-y-auto"
          style={{ backgroundColor: "var(--color-surface-2)" }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
