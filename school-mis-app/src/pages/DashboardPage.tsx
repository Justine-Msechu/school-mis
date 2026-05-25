import { useEffect, useState } from "react";
import {
  Users, GraduationCap, BookOpen, DollarSign,
  Calendar, Activity, Heart, AlertCircle,
  type LucideIcon,
} from "lucide-react";
import { getDashboardStats, type DashboardStats } from "@/api/dashboard";
import StatCard from "@/components/ui/StatCard";
import Card from "@/components/ui/Card";
import { useAuthStore } from "@/stores/authStore";

export default function DashboardPage() {
  const { user, can } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  };

  const val = (v: number | undefined) => (loading ? "—" : (v ?? 0));
  const fmtTzs = (v: number | undefined) => (loading ? "—" : (v ?? 0).toLocaleString());

  // Which KPI cards to show — each gated by permission
  const kpiCards = [
    can("student.view")   && { title: "Total Students",      value: val(stats?.students),              icon: Users,         color: "#7C3AED" },
    can("teachers.view")  && { title: "Teachers",             value: val(stats?.teachers),              icon: GraduationCap, color: "#0891B2" },
    can("classes.view")   && { title: "Classes",              value: val(stats?.classes),               icon: BookOpen,      color: "#059669" },
    can("finance.view")   && { title: "Pending Fees (TZS)",   value: fmtTzs(stats?.pending_fees),       icon: DollarSign,    color: "#D97706" },
    can("welfare.view")   && { title: "Active Welfare Cases", value: val(stats?.welfare_cases),         icon: AlertCircle,   color: "#DC2626" },
    can("health.view")    && { title: "Health Visits Today",  value: val(stats?.health_visits_today),   icon: Heart,         color: "#DB2777" },
  ].filter(Boolean) as { title: string; value: string | number; icon: LucideIcon; color: string }[];

  const showAttendance = can("attendance.view");
  const showActivity   = can("audit.view");

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting()}, {user?.full_name.split(" ")[0]} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {new Date().toLocaleDateString("en-US", {
            weekday: "long", year: "numeric", month: "long", day: "numeric",
          })}
        </p>
        {user?.role_label && (
          <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-xs font-medium text-white"
            style={{ backgroundColor: user.role_color ?? "#6B7280" }}>
            {user.role_label}
          </span>
        )}
      </div>

      {/* KPI cards — only what the user can see */}
      {kpiCards.length > 0 && (
        <div className={`grid grid-cols-2 lg:grid-cols-${Math.min(kpiCards.length, 4)} gap-4 mb-8`}>
          {kpiCards.map((card) => (
            <StatCard
              key={card.title}
              title={card.title}
              value={card.value}
              icon={card.icon}
              color={card.color}
            />
          ))}
        </div>
      )}

      {/* Second row — attendance + activity */}
      {(showAttendance || showActivity) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
          {showAttendance && (
            <StatCard
              title="Present Today"
              value={val(stats?.attendance_today)}
              subtitle={`${stats?.attendance_rate ?? 0}% attendance rate`}
              icon={Calendar}
              color="#0891B2"
              className={showActivity ? "lg:col-span-1" : "lg:col-span-3"}
            />
          )}

          {showActivity && (
            <Card className={`${showAttendance ? "lg:col-span-2" : "lg:col-span-3"} !p-0 overflow-hidden`}>
              <div className="flex items-center gap-2 px-5 py-3.5 border-b border-gray-100">
                <Activity size={15} className="text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-800">Recent Activity</h3>
              </div>
              <div className="divide-y divide-gray-50">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="px-5 py-3 flex items-center gap-3 animate-pulse">
                      <div className="w-6 h-6 rounded-full bg-gray-200 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="h-3 bg-gray-200 rounded w-3/4 mb-1.5" />
                        <div className="h-2.5 bg-gray-100 rounded w-1/2" />
                      </div>
                    </div>
                  ))
                ) : stats?.recent_activity?.length ? (
                  stats.recent_activity.slice(0, 8).map((a) => (
                    <div key={a.id} className="px-5 py-2.5 flex items-start gap-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-gray-700 truncate">{a.action}</p>
                        <p className="text-2xs text-gray-400 mt-0.5">
                          {a.user_name} · {a.module} · {new Date(a.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="px-5 py-6 text-xs text-gray-400 text-center">No recent activity</p>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Empty state — user has no permissions yet */}
      {kpiCards.length === 0 && !showAttendance && !showActivity && !loading && (
        <div className="text-center py-20 text-gray-400">
          <Users size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No dashboard data available for your current role.</p>
          <p className="text-xs mt-1">Contact your administrator to assign permissions.</p>
        </div>
      )}
    </div>
  );
}
