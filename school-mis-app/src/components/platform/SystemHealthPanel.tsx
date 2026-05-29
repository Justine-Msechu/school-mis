import { useEffect, useState, useCallback } from "react";
import {
  Activity, CheckCircle2, AlertTriangle, XCircle,
  RefreshCw, CheckCheck, Database, Zap, Building2,
} from "lucide-react";
import {
  getLiveStatus, getAlerts, resolveAlert,
  type LiveStatus, type HealthAlert,
} from "@/api/healthMonitor";

const LEVEL_STYLE = {
  critical: { bg: "bg-red-50",    border: "border-red-200",    text: "text-red-700",    icon: XCircle,        dot: "bg-red-500"    },
  warning:  { bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-700",  icon: AlertTriangle,  dot: "bg-amber-400"  },
};

const METRIC_LABEL: Record<string, string> = {
  db_connections:  "DB Connections",
  error_spike:     "Error Spike",
  expired_schools: "Expired Schools",
};

const METRIC_ICON: Record<string, React.ElementType> = {
  db_connections:  Database,
  error_spike:     Zap,
  expired_schools: Building2,
};

function StatusDot({ status }: { status: "ok" | "warning" | "critical" }) {
  if (status === "ok")       return <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />;
  if (status === "warning")  return <span className="w-2 h-2 rounded-full bg-amber-400 inline-block animate-pulse" />;
  return                            <span className="w-2 h-2 rounded-full bg-red-500 inline-block animate-pulse" />;
}

function GaugeBar({ pct, status }: { pct: number; status: "ok" | "warning" | "critical" }) {
  const color = status === "ok" ? "#10B981" : status === "warning" ? "#F59E0B" : "#EF4444";
  return (
    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden w-24">
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }} />
    </div>
  );
}

export default function SystemHealthPanel() {
  const [status,   setStatus]   = useState<LiveStatus | null>(null);
  const [alerts,   setAlerts]   = useState<HealthAlert[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [resolving, setResolving] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, a] = await Promise.all([getLiveStatus(), getAlerts(0)]);
      setStatus(s);
      setAlerts(a.items);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleResolve = async (id: number) => {
    setResolving(id);
    await resolveAlert(id).catch(() => {});
    setResolving(null);
    load();
  };

  const allOk = !loading && alerts.length === 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Activity size={15} className="text-gray-400" />
          <h2 className="font-semibold text-gray-900 text-sm">System Health</h2>
          {allOk && (
            <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
              <CheckCircle2 size={12} /> All systems OK
            </span>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-gray-50 text-gray-400 disabled:opacity-40"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-24">
          <RefreshCw size={18} className="animate-spin text-violet-400" />
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {/* Live metrics row */}
          {status && (
            <div className="px-5 py-3 flex flex-wrap gap-6">
              {/* DB connections */}
              <div className="flex items-center gap-2.5">
                <Database size={13} className="text-gray-400 flex-shrink-0" />
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <StatusDot status={status.db.status} />
                    <span className="text-xs font-medium text-gray-700">DB connections</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <GaugeBar pct={status.db.pct} status={status.db.status} />
                    <span className="text-xs text-gray-500">{status.db.connections}/{status.db.max} ({status.db.pct}%)</span>
                  </div>
                </div>
              </div>

              {/* Errors */}
              <div className="flex items-center gap-2.5">
                <Zap size={13} className={status.errors_5min >= 10 ? "text-amber-500" : "text-gray-400"} />
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <StatusDot status={status.errors_5min >= 25 ? "critical" : status.errors_5min >= 10 ? "warning" : "ok"} />
                    <span className="text-xs font-medium text-gray-700">Errors / 5 min</span>
                  </div>
                  <span className={`text-xs font-semibold ${status.errors_5min >= 10 ? "text-amber-600" : "text-gray-500"}`}>
                    {status.errors_5min}
                  </span>
                </div>
              </div>

              {/* Expired schools */}
              <div className="flex items-center gap-2.5">
                <Building2 size={13} className={status.expired_schools > 0 ? "text-amber-500" : "text-gray-400"} />
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <StatusDot status={status.expired_schools > 0 ? "warning" : "ok"} />
                    <span className="text-xs font-medium text-gray-700">Expired schools</span>
                  </div>
                  <span className={`text-xs font-semibold ${status.expired_schools > 0 ? "text-amber-600" : "text-gray-500"}`}>
                    {status.expired_schools}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Active alerts */}
          {alerts.length > 0 && (
            <div className="px-5 py-3 space-y-2">
              {alerts.map(alert => {
                const s   = LEVEL_STYLE[alert.level as "warning" | "critical"] ?? LEVEL_STYLE.warning;
                const Icon = METRIC_ICON[alert.metric] ?? AlertTriangle;
                return (
                  <div
                    key={alert.id}
                    className={`flex items-start gap-3 rounded-xl px-3 py-2.5 border ${s.bg} ${s.border}`}
                  >
                    <Icon size={14} className={`${s.text} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-semibold ${s.text}`}>
                          {METRIC_LABEL[alert.metric] ?? alert.metric}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wide ${s.bg} ${s.text} border ${s.border}`}>
                          {alert.level}
                        </span>
                      </div>
                      <p className={`text-xs mt-0.5 ${s.text}`}>{alert.message}</p>
                    </div>
                    <button
                      onClick={() => handleResolve(alert.id)}
                      disabled={resolving === alert.id}
                      className="flex-shrink-0 flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                      title="Mark resolved"
                    >
                      <CheckCheck size={11} />
                      {resolving === alert.id ? "…" : "Resolve"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {!loading && allOk && (
            <div className="px-5 py-3 flex items-center gap-2 text-xs text-emerald-600">
              <CheckCircle2 size={13} /> No active alerts
            </div>
          )}
        </div>
      )}
    </div>
  );
}
