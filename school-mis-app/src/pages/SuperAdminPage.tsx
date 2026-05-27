import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, RefreshCw, CheckCircle, XCircle, Clock, Users, LogIn } from "lucide-react";
import { getSuperAdminSchools, updateSchoolSubscription, type SchoolRow } from "@/api/schools";
import { useImpersonationStore } from "@/stores/impersonationStore";

const PLANS = ["trial", "basic", "standard", "premium"] as const;
const STATUSES = ["trial", "active", "expired", "cancelled"] as const;

const STATUS_BADGE: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  active:    { label: "Active",    color: "#059669", icon: CheckCircle },
  trial:     { label: "Trial",     color: "#0891B2", icon: Clock },
  expired:   { label: "Expired",   color: "#DC2626", icon: XCircle },
  cancelled: { label: "Cancelled", color: "#6B7280", icon: XCircle },
};

const PLAN_COLOR: Record<string, string> = {
  trial:    "#0891B2",
  basic:    "#0891B2",
  standard: "#7C3AED",
  premium:  "#059669",
};

interface EditModal {
  school: SchoolRow;
  plan:       string;
  status:     string;
  trial_ends: string;
}

export default function SuperAdminPage() {
  const navigate = useNavigate();
  const { enter } = useImpersonationStore();
  const [schools, setSchools]     = useState<SchoolRow[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");
  const [modal, setModal]         = useState<EditModal | null>(null);
  const [saving, setSaving]       = useState(false);
  const [saveError, setSaveError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await getSuperAdminSchools();
      setSchools(res.data);
    } catch {
      setError("Failed to load schools.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openModal = (school: SchoolRow) =>
    setModal({
      school,
      plan:       school.plan,
      status:     school.subscription_status,
      trial_ends: school.trial_ends ?? "",
    });

  const handleSave = async () => {
    if (!modal) return;
    setSaving(true); setSaveError("");
    try {
      await updateSchoolSubscription(modal.school.id, {
        plan:        modal.plan,
        status:      modal.status,
        trial_ends:  modal.trial_ends || undefined,
      });
      setModal(null);
      await load();
    } catch {
      setSaveError("Failed to update subscription.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Admin</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage all registered schools and subscriptions</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total schools",  value: schools.length },
          { label: "Active",         value: schools.filter(s => s.subscription_status === "active").length },
          { label: "On trial",       value: schools.filter(s => s.subscription_status === "trial").length },
          { label: "Expired",        value: schools.filter(s => s.subscription_status === "expired" || s.subscription_status === "cancelled").length },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-16 text-red-500 text-sm">{error}</div>
        ) : schools.length === 0 ? (
          <div className="text-center py-16">
            <Building2 size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 text-sm">No schools registered yet.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {["School", "Plan", "Status", "Trial ends", "Users", "Admin", "Actions"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schools.map((s) => {
                const badge = STATUS_BADGE[s.subscription_status] ?? STATUS_BADGE.trial;
                const BadgeIcon = badge.icon;
                return (
                  <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                          <Building2 size={14} className="text-violet-600" />
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{s.name}</p>
                          <p className="text-xs text-gray-400">{s.email ?? "—"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-semibold"
                        style={{ backgroundColor: `${PLAN_COLOR[s.plan]}15`, color: PLAN_COLOR[s.plan] }}
                      >
                        {s.plan.charAt(0).toUpperCase() + s.plan.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <BadgeIcon size={12} style={{ color: badge.color }} />
                        <span className="text-xs font-medium" style={{ color: badge.color }}>{badge.label}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.trial_ends ?? "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-gray-500">
                        <Users size={12} />
                        {s.user_count}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.admin_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { enter(s.id, s.name); navigate("/"); }}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                          title="Enter this school as Administrator"
                        >
                          <LogIn size={11} /> Enter
                        </button>
                        <button
                          onClick={() => openModal(s)}
                          className="px-3 py-1.5 text-xs font-medium text-violet-600 border border-violet-200 rounded-lg hover:bg-violet-50 transition-colors"
                        >
                          Manage
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">{modal.school.name}</h2>
            <p className="text-xs text-gray-400 mb-5">Update subscription plan and status</p>

            {saveError && (
              <div className="mb-4 px-3 py-2.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                {saveError}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Plan</label>
                <select
                  value={modal.plan}
                  onChange={(e) => setModal((m) => m && { ...m, plan: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {PLANS.map(p => (
                    <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Status</label>
                <select
                  value={modal.status}
                  onChange={(e) => setModal((m) => m && { ...m, status: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {STATUSES.map(s => (
                    <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Trial / expiry date
                </label>
                <input
                  type="date"
                  value={modal.trial_ends}
                  onChange={(e) => setModal((m) => m && { ...m, trial_ends: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                />
              </div>
            </div>

            <div className="flex gap-2.5 mt-6">
              <button
                onClick={() => { setModal(null); setSaveError(""); }}
                className="flex-1 py-2.5 text-sm font-medium text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 py-2.5 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-60 rounded-xl transition-colors"
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
