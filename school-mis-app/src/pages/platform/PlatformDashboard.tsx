import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, Users, CheckCircle, Clock, XCircle,
  TrendingUp, RefreshCw, ArrowRight, AlertTriangle,
  LogIn, BarChart3, GraduationCap, BookOpen, PauseCircle,
} from "lucide-react";
import { getPlatformStats, type PlatformStats } from "@/api/schools";
import { useImpersonationStore } from "@/stores/impersonationStore";

const PLAN_COLOR: Record<string, string> = {
  trial:    "#0891B2",
  basic:    "#2563EB",
  standard: "#7C3AED",
  premium:  "#059669",
};

const STATUS_COLOR: Record<string, string> = {
  active:    "#059669",
  trial:     "#0891B2",
  expired:   "#DC2626",
  cancelled: "#6B7280",
};

export default function PlatformDashboard() {
  const navigate      = useNavigate();
  const { enter }     = useImpersonationStore();
  const [stats,   setStats]   = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await getPlatformStats();
      setStats(res.data);
    } catch {
      setError("Failed to load platform stats. Check the server is running and migration has completed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleEnter = (id: number, name: string) => {
    enter(id, name);
    navigate("/");
  };

  const statCards = stats ? [
    { label: "Total Schools",  value: stats.total_schools,  icon: Building2,      color: "#7C3AED" },
    { label: "Active",         value: stats.active,         icon: CheckCircle,    color: "#059669" },
    { label: "On Trial",       value: stats.trial,          icon: Clock,          color: "#0891B2" },
    { label: "Expired",        value: stats.expired,        icon: XCircle,        color: "#DC2626" },
    { label: "Suspended",      value: stats.suspended ?? 0, icon: PauseCircle,    color: "#F59E0B" },
    { label: "New This Week",  value: stats.new_this_week,  icon: TrendingUp,     color: "#10B981" },
    { label: "Total Users",    value: stats.total_users,    icon: Users,          color: "#6366F1" },
    { label: "Total Students", value: stats.total_students, icon: GraduationCap,  color: "#0891B2" },
    { label: "Total Teachers", value: stats.total_teachers, icon: BookOpen,       color: "#7C3AED" },
  ] : [];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">System-wide statistics across all registered schools</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Loading / error */}
      {loading && (
        <div className="flex items-center justify-center h-48">
          <div className="w-7 h-7 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && stats && (
        <>
          {/* Expiring soon alert */}
          {stats.expiring_soon > 0 && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-amber-800 text-sm">
                    {stats.expiring_soon} school{stats.expiring_soon !== 1 ? "s" : ""} expiring within 7 days
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {stats.expiring_list.map(s => (
                      <div key={s.id} className="flex items-center gap-2 bg-white rounded-lg px-3 py-1.5 border border-amber-200 text-xs">
                        <span className="font-medium text-gray-800">{s.name}</span>
                        <span className="text-amber-600">expires {s.trial_ends}</span>
                        <button
                          onClick={() => handleEnter(s.id, s.name)}
                          className="text-violet-600 hover:underline font-medium"
                        >
                          Enter
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-9 gap-4">
            {statCards.map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                  style={{ backgroundColor: `${color}18` }}>
                  <Icon size={15} style={{ color }} />
                </div>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
                <p className="text-xs text-gray-500 mt-0.5 leading-tight">{label}</p>
              </div>
            ))}
          </div>

          {/* Two-column section */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* By plan distribution */}
            <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 size={16} className="text-gray-400" />
                <h2 className="font-semibold text-gray-900 text-sm">Schools by Plan</h2>
              </div>
              {stats.total_schools === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">No schools registered yet.</p>
              ) : (
                <div className="space-y-3">
                  {(["premium", "standard", "basic", "trial"] as const).map(plan => {
                    const count = stats.by_plan[plan] ?? 0;
                    if (count === 0) return null;
                    const pct = Math.round((count / (stats.total_schools || 1)) * 100);
                    return (
                      <div key={plan}>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="font-medium capitalize" style={{ color: PLAN_COLOR[plan] }}>{plan}</span>
                          <span className="text-gray-500 text-xs">{count} school{count !== 1 ? "s" : ""} · {pct}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${pct}%`, backgroundColor: PLAN_COLOR[plan] }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Recent registrations */}
            <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 text-sm">Recent Registrations</h2>
                <button
                  onClick={() => navigate("/platform/schools")}
                  className="text-xs text-violet-600 hover:underline flex items-center gap-1"
                >
                  View all <ArrowRight size={11} />
                </button>
              </div>
              {stats.recent_schools.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">No schools registered yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {stats.recent_schools.map(s => (
                    <div key={s.id} className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-50 transition-colors">
                      <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                        <Building2 size={14} className="text-violet-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{s.name}</p>
                        <p className="text-xs text-gray-400 truncate">{s.admin_name ?? "—"}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                          className="text-xs font-semibold px-2 py-0.5 rounded-full capitalize"
                          style={{
                            backgroundColor: `${STATUS_COLOR[s.subscription_status] ?? "#94A3B8"}15`,
                            color: STATUS_COLOR[s.subscription_status] ?? "#94A3B8",
                          }}
                        >
                          {s.subscription_status}
                        </span>
                        <button
                          onClick={() => handleEnter(s.id, s.name)}
                          className="flex items-center gap-1 text-xs px-2.5 py-1 text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                        >
                          <LogIn size={11} /> Enter
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick links */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Manage Schools",     desc: "View and manage all schools",     to: "/platform/schools",  color: "#7C3AED" },
              { label: "Audit Log",          desc: "Track platform activity",         to: "/platform/audit",    color: "#0891B2" },
              { label: "Register a School",  desc: "Manually add a new school",       to: "/register",               color: "#059669" },
              { label: "Module Access",      desc: "Control plan feature flags",      to: "/platform/features",      color: "#7C3AED" },
              { label: "Announcements",      desc: "Broadcast notices to schools",    to: "/platform/announcements", color: "#F59E0B" },
              { label: "Platform Settings",  desc: "Admin account settings",          to: "/platform/settings",      color: "#6366F1" },
            ].map(({ label, desc, to, color }) => (
              <button
                key={to}
                onClick={() => navigate(to)}
                className="text-left p-4 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5"
              >
                <div className="w-7 h-7 rounded-lg mb-2.5 flex items-center justify-center"
                  style={{ backgroundColor: `${color}18` }}>
                  <ArrowRight size={13} style={{ color }} />
                </div>
                <p className="text-sm font-semibold text-gray-900">{label}</p>
                <p className="text-xs text-gray-400 mt-0.5 leading-tight">{desc}</p>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
