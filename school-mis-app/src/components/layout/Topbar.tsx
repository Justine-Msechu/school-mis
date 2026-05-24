import { useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";

const LABELS: Record<string, string> = {
  "":           "Dashboard",
  students:     "Students",
  teachers:     "Teachers",
  classes:      "Classes",
  grades:       "Grades & Examinations",
  attendance:   "Attendance",
  library:      "Library",
  finance:      "Finance",
  accounting:   "Accounting",
  transport:    "Transport",
  inventory:    "Inventory",
  health:       "Health",
  welfare:      "Welfare",
  promotion:    "Promotion",
  reports:      "Reports",
  settings:     "Settings",
};

export default function Topbar() {
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
    <header className="h-14 flex items-center px-6 bg-white border-b border-gray-200 flex-shrink-0">
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        {crumbs.map((c, i) => (
          <span key={c.href} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={13} className="text-gray-300" />}
            <span className={i === crumbs.length - 1 ? "font-semibold text-gray-900" : "hover:text-gray-700"}>
              {c.label}
            </span>
          </span>
        ))}
      </nav>
    </header>
  );
}
