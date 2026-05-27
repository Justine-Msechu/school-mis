import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, Users, CheckCircle, Clock, XCircle,
  TrendingUp, RefreshCw, ArrowRight,
} from "lucide-react";
import { getPlatformStats, type PlatformStats } from "@/api/schools";
import { useImpersonationStore } from "@/stores/impersonationStore";

const PLAN_COLOR: Record<string, string> = {
  trial:    "#0891B2",
  basic:    "#0891B2",
  standard: "#7C3AED",
  premium:  "#059669",
};

const STATUS_ICON = {
  active:    { icon: CheckCircle, color: "#059669" },
  trial:     { icon: Clock,       color: "#0891B2" },
  expired:   { icon: XCircle,     color: "#DC2626" },
  cancelled: { icon: XCircle,     color: "#6B7280" },
};

export default function PlatformDashboard() {
  const navigate = useNavigate();
  const { enter } = useImpersonationStore();
  const [stats,   setStats]   = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await getPlatformStats();
      setStats(res.data);
    } catch {
      setError("Failed to load platform stats.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleEnterSchool = (id: number, name: string) => {
    enter(id, name);
    navigate("/");
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (error) return (
    <div className="p-6 text-red-500 text-sm">{error}</div>
  );

  if (!stats) return null;

  const statCards = [
    { label: "Total Schools",   value: stats.total_schools, icon: Building2,   color: "#7C3AED" },
    { label: "Active",          value: stats.active,        icon: CheckCircle, color: "#059669" },
    { label: "On Trial",        value: stats.trial,         icon: Clock,       color: "#0891B2" },
    { label: "Expired",         value: stats.expired,       icon: XCircle,     color: "#DC2626" },
    { label: "Total Users",     value: stats.total_users,   icon: Users,       color: "#F59E0B" },
    { label: "New This Week",   value: stats.new_this_week, icon: TrendingUp,  color: "#10B981" },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">System-wide statistics across all registered schools</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3" style={{ backgroundColor: `${color}15` }}>
              <Icon size={16} style={{ color }} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* By plan */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">Schools by Plan</h2>
          <div className="space-y-3">
            {["trial", "basic", "standard", "premium"].map(plan => {
              const count = stats.by_plan[plan] ?? 0;
              const total = stats.total_schools || 1;
              const pct   = Math.round((count / total) * 100);
              return (
                <div key={plan}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="font-medium capitalize" style={{ color: PLAN_COLOR[plan] }}>{plan}</span>
                    <span className="text-gray-500">{count} school{count !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: PLAN_COLOR[plan] }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent registrations */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Registrations</h2>
            <button onClick={() => navigate("/platform/schools")} className="text-xs text-violet-600 hover:underline flex items-center gap-1">
              View all <ArrowRight size={11} />
            </button>
          </div>
          <div className="space-y-3">
            {stats.recent_schools.length === 0 && (
              <p className="text-sm text-gray-400">No schools registered yet.</p>
            )}
            {stats.recent_schools.map((s) => {
              const st = STATUS_ICON[s.subscription_status as keyof typeof STATUS_ICON] ?? STATUS_ICON.trial;
              const StatusIcon = st.icon;
              return (
                <div key={s.id} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                    <Building2 size={14} className="text-violet-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{s.name}</p>
                    <p className="text-xs text-gray-400">{s.admin_name ?? "—"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium capitalize" style={{ color: PLAN_COLOR[s.plan] }}>{s.plan}</span>
                    <StatusIcon size={13} style={{ color: st.color }} />
                  </div>
                  <button
                    onClick={() => handleEnterSchool(s.id, s.name)}
                    className="text-xs px-2 py-1 text-violet-600 border border-violet-200 rounded-lg hover:bg-violet-50 flex-shrink-0"
                  >
                    Enter
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
