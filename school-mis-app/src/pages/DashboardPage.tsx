import { useEffect, useState } from "react";
import { Users, GraduationCap, BookOpen, DollarSign, Calendar, Activity } from "lucide-react";
import { getDashboardStats, type DashboardStats } from "@/api/dashboard";
import StatCard from "@/components/ui/StatCard";
import Card from "@/components/ui/Card";
import { useAuthStore } from "@/stores/authStore";

export default function DashboardPage() {
  const { user } = useAuthStore();
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

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting()}, {user?.full_name.split(" ")[0]} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Students"
          value={loading ? "—" : stats?.students ?? 0}
          icon={Users}
          color="#7C3AED"
        />
        <StatCard
          title="Teachers"
          value={loading ? "—" : stats?.teachers ?? 0}
          icon={GraduationCap}
          color="#0891B2"
        />
        <StatCard
          title="Classes"
          value={loading ? "—" : stats?.classes ?? 0}
          icon={BookOpen}
          color="#059669"
        />
        <StatCard
          title="Pending Fees (TZS)"
          value={loading ? "—" : (stats?.pending_fees ?? 0).toLocaleString()}
          icon={DollarSign}
          color="#D97706"
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <StatCard
          title="Present Today"
          value={loading ? "—" : stats?.attendance_today ?? 0}
          subtitle={`${stats?.attendance_rate ?? 0}% attendance rate`}
          icon={Calendar}
          color="#0891B2"
          className="lg:col-span-1"
        />

        {/* Recent Activity */}
        <Card className="lg:col-span-2 !p-0 overflow-hidden">
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
            ) : stats?.recent_activity.length ? (
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
      </div>
    </div>
  );
}
