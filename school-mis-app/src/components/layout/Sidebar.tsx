import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clsx } from "clsx";
import {
  LayoutDashboard, Users, GraduationCap, BookOpen,
  Award, Calendar, Library, DollarSign, Building2,
  Bus, Package, Heart, HandHeart, TrendingUp,
  BarChart2, Settings, LogOut, ChevronDown, Shield,
  UserCheck, FileText, UsersRound, ShieldCheck, Banknote,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { logout } from "@/api/auth";

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
      { icon: Award,      label: "Grades",        to: "/grades",        perm: "grades.view" },
      { icon: Calendar,   label: "Attendance",    to: "/attendance",    perm: "attendance.view" },
      { icon: UserCheck,  label: "Enrollment",    to: "/enrollment",    perm: "enrollment.view" },
      { icon: FileText,   label: "Report Cards",  to: "/report-cards",  perm: "report_cards.view" },
      { icon: Library,    label: "Library",       to: "/library",       perm: "library.view" },
    ],
  },
  {
    label: "People",
    items: [
      { icon: Users,       label: "Students",   to: "/students",   perm: "student.view" },
      { icon: GraduationCap, label: "Teachers", to: "/teachers",   perm: "teachers.view" },
      { icon: UsersRound,  label: "Guardians",  to: "/guardians",  perm: "guardian.view" },
      { icon: BookOpen,    label: "Classes",    to: "/classes",    perm: "classes.view" },
    ],
  },
  {
    label: "Operations",
    items: [
      { icon: DollarSign,  label: "Finance",    to: "/finance",    perm: "finance.view" },
      { icon: Banknote,    label: "Payroll",    to: "/payroll",    perm: "payroll.view" },
      { icon: Building2,   label: "Accounting", to: "/accounting", perm: "accounting.view" },
      { icon: Bus,         label: "Transport",  to: "/transport",  perm: "transport.view" },
      { icon: Package,     label: "Inventory",  to: "/inventory",  perm: "inventory.view" },
    ],
  },
  {
    label: "Welfare",
    items: [
      { icon: Heart,      label: "Health",    to: "/health",    perm: "health.view" },
      { icon: HandHeart,  label: "Welfare",   to: "/welfare",   perm: "welfare.view" },
      { icon: TrendingUp, label: "Promotion", to: "/promotion", perm: "student.promote" },
    ],
  },
  {
    label: "System",
    items: [
      { icon: BarChart2,    label: "Reports",       to: "/reports",   perm: "reports.view" },
      { icon: Settings,     label: "Settings",      to: "/settings",  perm: "settings.view" },
      { icon: ShieldCheck,  label: "Roles & Access",to: "/rbac",      roles: ["admin"] },
      { icon: Shield,       label: "Audit Log",     to: "/audit",     perm: "audit.view" },
    ],
  },
];

function NavItemEl({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        clsx(
          "flex items-center gap-2.5 px-3 h-9 rounded-lg text-sm transition-colors relative",
          isActive
            ? "bg-white/14 text-white font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-5 before:w-0.5 before:bg-violet-400 before:rounded-full"
            : "text-sidebar-text hover:bg-white/8 hover:text-gray-200"
        )
      }
    >
      <Icon size={16} className="flex-shrink-0" />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
}

function NavGroupEl({ group }: { group: NavGroupDef }) {
  const [open, setOpen] = useState(true);
  const { can, user } = useAuthStore();

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
          {visible.map((item) => <NavItemEl key={item.to} item={item} />)}
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
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

  return (
    <aside className="flex flex-col w-[220px] min-h-screen bg-sidebar-bg flex-shrink-0">
      {/* Brand header */}
      <div className="px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <BookOpen size={15} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-white leading-tight truncate">School MIS</p>
            <p className="text-2xs text-sidebar-text">Management System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-0.5">
        {NAV_GROUPS.map((g, i) => <NavGroupEl key={i} group={g} />)}
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
}
