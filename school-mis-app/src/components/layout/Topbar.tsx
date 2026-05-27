import { useRef, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChevronRight, Menu, Sun, Moon, Waves, Palette } from "lucide-react";
import NotificationBell from "./NotificationBell";
import { useThemeStore, THEMES, type Theme } from "@/stores/themeStore";

const THEME_ICONS: Record<Theme, React.ReactNode> = {
  light: <Sun size={15} />,
  dark:  <Moon size={15} />,
  blue:  <Waves size={15} />,
};

function ThemeSwitcher() {
  const { theme, setTheme } = useThemeStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title="Change theme"
        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-[#252d3d] text-gray-500 dark:text-gray-400 hover:text-gray-700 transition-colors"
        style={{ color: "var(--color-on-surface-muted)" }}
      >
        <Palette size={17} />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-1.5 rounded-xl shadow-lg border py-1 z-50 min-w-[140px]"
          style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
        >
          {THEMES.map((t) => (
            <button
              key={t.key}
              onClick={() => { setTheme(t.key); setOpen(false); }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-sm transition-colors text-left"
              style={{
                color: theme === t.key ? "var(--color-accent)" : "var(--color-on-surface)",
                backgroundColor: theme === t.key ? "var(--color-accent-light)" : "transparent",
              }}
            >
              <span style={{ color: t.preview }}>{THEME_ICONS[t.key]}</span>
              {t.label}
              {theme === t.key && <span className="ml-auto text-xs">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const LABELS: Record<string, string> = {
  "":             "Dashboard",
  students:       "Students",
  teachers:       "Teachers",
  classes:        "Classes",
  grades:         "Grades & Examinations",
  attendance:     "Attendance",
  library:        "Library",
  finance:        "Finance",
  accounting:     "Accounting",
  transport:      "Transport",
  inventory:      "Inventory",
  health:         "Health",
  welfare:        "Welfare",
  promotion:      "Promotion",
  reports:        "Reports",
  settings:       "Settings",
  audit:          "Audit Log",
  enrollment:     "Enrollment",
  guardians:      "Guardians",
  "report-cards": "Report Cards",
  rbac:           "Roles & Access",
  payroll:        "Payroll",
  ngo:            "NGO Partners",
};

interface TopbarProps {
  onMenuClick: () => void;
}

export default function Topbar({ onMenuClick }: TopbarProps) {
  const { pathname } = useLocation();
  const segments = pathname.split("/").filter(Boolean);

  const crumbs = [
    { label: "Home", href: "/" },
    ...segments.map((seg, i) => ({
      label: LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1),
      href: "/" + segments.slice(0, i + 1).join("/"),
    })),
  ];

  return (
    <header
      className="h-14 flex items-center px-4 md:px-6 flex-shrink-0 gap-3 border-b"
      style={{ background: "var(--color-topbar-bg)", borderColor: "var(--color-topbar-border)" }}
    >
      <button
        onClick={onMenuClick}
        className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors flex-shrink-0"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      <nav className="flex-1 flex items-center gap-1 text-sm text-gray-500 overflow-hidden">
        {crumbs.map((c, i) => (
          <span key={c.href} className="flex items-center gap-1 min-w-0">
            {i > 0 && <ChevronRight size={13} className="text-gray-300 flex-shrink-0" />}
            <span className={`truncate ${i === crumbs.length - 1 ? "font-semibold text-gray-900" : "hover:text-gray-700 hidden sm:inline"}`}
              style={i === crumbs.length - 1 ? { color: "var(--color-on-surface)" } : {}}>
              {c.label}
            </span>
          </span>
        ))}
        {crumbs.length > 1 && (
          <span className="sm:hidden font-semibold truncate" style={{ color: "var(--color-on-surface)" }}>
            {crumbs[crumbs.length - 1].label}
          </span>
        )}
      </nav>

      <ThemeSwitcher />
      <NotificationBell />
    </header>
  );
}
