import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clsx } from "clsx";
import {
  LayoutDashboard, Users, GraduationCap, BookOpen,
  Award, Calendar, CalendarDays, Library, DollarSign, Building2,
  Bus, Package, Heart, HandHeart, TrendingUp,
  BarChart2, Settings, LogOut, ChevronDown, Shield,
  UserCheck, FileText, UsersRound, ShieldCheck, Banknote, Handshake, X,
  CreditCard, Lock,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useSubscriptionStore } from "@/stores/subscriptionStore";
import { logout } from "@/api/auth";

// Modules blocked per plan — must match backend plan_config.py
const PLAN_RESTRICTED: Record<string, string[]> = {
  basic:    ["/payroll", "/welfare", "/transport", "/inventory", "/library", "/ngo", "/accounting"],
  standard: [],
  premium:  [],
};

interface NavItem {
  icon: LucideIcon;
  label: string;
  to: string;
  perm?: string;
  roles?: string[];
}

interface NavGroupDef {
  label: string | null;
  items: NavItem[];
}

const NAV_GROUPS: NavGroupDef[] = [
  {
    label: null,
    items: [{ icon: LayoutDashboard, label: "Dashboard", to: "/" }],
  },
  {
    label: "Academics",
    items: [
      { icon: Award,        label: "Grades",        to: "/grades",        perm: "grades.view" },
      { icon: Calendar,     label: "Attendance",    to: "/attendance",    perm: "attendance.view" },
      { icon: CalendarDays, label: "Timetable",     to: "/timetable",     perm: "timetable.view" },
      { icon: UserCheck,    label: "Enrollment",    to: "/enrollment",    perm: "enrollment.view" },
      { icon: FileText,     label: "Report Cards",  to: "/report-cards",  perm: "report_cards.view" },
      { icon: Library,      label: "Library",       to: "/library",       perm: "library.view" },
    ],
  },
  {
    label: "People",
    items: [
      { icon: Users,         label: "Students",  to: "/students",  perm: "student.view" },
      { icon: GraduationCap, label: "Teachers",  to: "/teachers",  perm: "teachers.view" },
      { icon: UsersRound,    label: "Guardians", to: "/guardians", perm: "guardian.view" },
      { icon: BookOpen,      label: "Classes",   to: "/classes",   perm: "classes.view" },
    ],
  },
  {
    label: "Operations",
    items: [
      { icon: DollarSign, label: "Finance",    to: "/finance",    perm: "finance.view" },
      { icon: Banknote,   label: "Payroll",    to: "/payroll",    perm: "payroll.view" },
      { icon: Building2,  label: "Accounting", to: "/accounting", perm: "accounting.view" },
      { icon: Bus,        label: "Transport",  to: "/transport",  perm: "transport.view" },
      { icon: Package,    label: "Inventory",  to: "/inventory",  perm: "inventory.view" },
    ],
  },
  {
    label: "Welfare",
    items: [
      { icon: Heart,      label: "Health",       to: "/health",    perm: "health.view" },
      { icon: HandHeart,  label: "Welfare",      to: "/welfare",   perm: "welfare.view" },
      { icon: Handshake,  label: "NGO Partners", to: "/ngo",       perm: "ngo.view" },
      { icon: TrendingUp, label: "Promotion",    to: "/promotion", perm: "student.promote" },
    ],
  },
  {
    label: "System",
    items: [
      { icon: BarChart2,   label: "Reports",        to: "/reports",  perm: "reports.view" },
      { icon: Settings,    label: "Settings",       to: "/settings", perm: "settings.view" },
      { icon: ShieldCheck, label: "Roles & Access", to: "/rbac",         roles: ["admin"] },
      { icon: Shield,      label: "Audit Log",      to: "/audit",        perm: "audit.view" },
      { icon: CreditCard,  label: "Subscription",   to: "/subscription", roles: ["admin"] },
    ],
  },
];

function NavItemEl({ item, onNavigate, locked }: { item: NavItem; onNavigate: () => void; locked?: boolean }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      onClick={onNavigate}
      className={({ isActive }) =>
        clsx(
          "flex items-center gap-2.5 px-3 h-9 rounded-lg text-sm transition-colors relative",
          locked
            ? "text-sidebar-text/40 cursor-default"
            : isActive
              ? "bg-white/14 text-white font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-5 before:w-0.5 before:bg-violet-400 before:rounded-full"
              : "text-sidebar-text hover:bg-white/8 hover:text-gray-200"
        )
      }
    >
      <Icon size={16} className="flex-shrink-0" />
      <span className="truncate flex-1">{item.label}</span>
      {locked && <Lock size={10} className="flex-shrink-0 opacity-50" />}
    </NavLink>
  );
}

function NavGroupEl({ group, onNavigate }: { group: NavGroupDef; onNavigate: () => void }) {
  const [open, setOpen] = useState(true);
  const { can, user } = useAuthStore();
  const plan = useSubscriptionStore((s) => s.plan);
  const restricted = PLAN_RESTRICTED[plan] ?? [];

  const visible = group.items.filter((i) => {
    if (i.roles && !i.roles.includes(user?.role ?? "")) return false;
    if (i.perm && !can(i.perm)) return false;
    return true;
  });
  if (visible.length === 0) return null;

  return (
    <div className="mt-1">
      {group.label && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center justify-between w-full px-3 py-1.5 mb-0.5"
        >
          <span className="text-2xs font-semibold uppercase tracking-wider text-sidebar-heading">
            {group.label}
          </span>
          <ChevronDown
            size={12}
            className={clsx("text-sidebar-heading transition-transform", !open && "-rotate-90")}
          />
        </button>
      )}
      {open && (
        <div className="flex flex-col gap-0.5">
          {visible.map((item) => (
            <NavItemEl
              key={item.to}
              item={item}
              onNavigate={onNavigate}
              locked={user?.role !== "admin" && restricted.some(p => item.to.startsWith(p))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout: storeLogout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); } catch { /* ignore */ }
    storeLogout();
    navigate("/login");
  };

  const roleColor = user?.role_color ?? "#94A3B8";
  const initials = user?.full_name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase() ?? "?";

  const sidebarContent = (
    <aside className="flex flex-col w-[220px] h-full bg-sidebar-bg">
      {/* Brand header */}
      <div className="px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <BookOpen size={15} className="text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold text-white leading-tight truncate">School MIS</p>
            <p className="text-2xs text-sidebar-text">Management System</p>
          </div>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="md:hidden p-1 rounded text-sidebar-text hover:text-white"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-0.5">
        {NAV_GROUPS.map((g, i) => (
          <NavGroupEl key={i} group={g} onNavigate={onClose} />
        ))}
      </nav>

      {/* User strip */}
      <div className="px-2 pb-3">
        <div className="border border-sidebar-border rounded-xl p-3 bg-sidebar-border/40">
          <div className="flex items-center gap-2.5 mb-2">
            <div
              className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
              style={{ background: roleColor }}
            >
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
              <p className="text-2xs truncate" style={{ color: roleColor }}>{user?.role_label}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-2xs text-sidebar-text hover:text-red-400 transition-colors"
          >
            <LogOut size={12} />
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop: always visible */}
      <div className="hidden md:flex flex-shrink-0 min-h-screen">
        {sidebarContent}
      </div>

      {/* Mobile: slide-over drawer */}
      {open && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={onClose}
          />
          {/* Drawer panel */}
          <div className="relative flex-shrink-0">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
