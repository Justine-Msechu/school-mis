import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, RefreshCw, CheckCircle, XCircle, Clock, Users,
  LogIn, Search, PauseCircle, PlayCircle, KeyRound, X, Copy, Check,
} from "lucide-react";
import {
  getSuperAdminSchools, updateSchoolSubscription,
  suspendSchool, activateSchool, resetAdminPassword,
  type SchoolRow,
} from "@/api/schools";
import { useImpersonationStore } from "@/stores/impersonationStore";

const PLANS    = ["trial", "basic", "standard", "premium"] as const;
const STATUSES = ["trial", "active", "expired", "cancelled", "suspended"] as const;

const PLAN_COLOR: Record<string, string> = {
  trial:    "#0891B2",
  basic:    "#0891B2",
  standard: "#7C3AED",
  premium:  "#059669",
};

const STATUS_META: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  active:    { label: "Active",    color: "#059669", icon: CheckCircle },
  trial:     { label: "Trial",     color: "#0891B2", icon: Clock },
  expired:   { label: "Expired",   color: "#DC2626", icon: XCircle },
  cancelled: { label: "Cancelled", color: "#6B7280", icon: XCircle },
  suspended: { label: "Suspended", color: "#F59E0B", icon: PauseCircle },
};

type FilterTab = "all" | "active" | "trial" | "suspended" | "expired";

interface ManageModal {
  school:     SchoolRow;
  plan:       string;
  status:     string;
  trial_ends: string;
}

interface ResetResult {
  schoolName: string;
  password:   string;
  copied:     boolean;
}

export default function SuperAdminPage() {
  const navigate = useNavigate();
  const { enter } = useImpersonationStore();

  const [schools, setSchools]       = useState<SchoolRow[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error,   setError]         = useState("");
  const [search,  setSearch]        = useState("");
  const [filter,  setFilter]        = useState<FilterTab>("all");
  const [modal,   setModal]         = useState<ManageModal | null>(null);
  const [saving,  setSaving]        = useState(false);
  const [saveError, setSaveError]   = useState("");
  const [actionId, setActionId]     = useState<number | null>(null);
  const [resetResult, setResetResult] = useState<ResetResult | null>(null);

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

  const openModal = (school: SchoolRow) => {
    setSaveError("");
    setModal({ school, plan: school.plan, status: school.subscription_status, trial_ends: school.trial_ends ?? "" });
  };

  const handleSave = async () => {
    if (!modal) return;
    setSaving(true); setSaveError("");
    try {
      await updateSchoolSubscription(modal.school.id, {
        plan: modal.plan, status: modal.status,
        trial_ends: modal.trial_ends || undefined,
      });
      setModal(null);
      await load();
    } catch {
      setSaveError("Failed to update subscription.");
    } finally { setSaving(false); }
  };

  const handleSuspend = async (school: SchoolRow) => {
    if (!confirm(`Suspend "${school.name}"? All users will be locked out.`)) return;
    setActionId(school.id);
    try {
      await suspendSchool(school.id);
      await load();
    } finally { setActionId(null); }
  };

  const handleActivate = async (school: SchoolRow) => {
    setActionId(school.id);
    try {
      await activateSchool(school.id);
      await load();
    } finally { setActionId(null); }
  };

  const handleResetPassword = async (school: SchoolRow) => {
    if (!confirm(`Reset admin password for "${school.name}"? The admin will be forced to change it on next login.`)) return;
    setActionId(school.id);
    try {
      const res = await resetAdminPassword(school.id);
      setResetResult({ schoolName: school.name, password: res.data.temp_password, copied: false });
      if (modal) setModal(null);
    } finally { setActionId(null); }
  };

  const copyPassword = () => {
    if (!resetResult) return;
    navigator.clipboard.writeText(resetResult.password).then(() =>
      setResetResult(r => r ? { ...r, copied: true } : r)
    );
  };

  const filtered = schools.filter(s => {
    const matchSearch = !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.admin_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (s.email ?? "").toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" || s.subscription_status === filter ||
      (filter === "expired" && (s.subscription_status === "expired" || s.subscription_status === "cancelled"));
    return matchSearch && matchFilter;
  });

  const filterCounts: Record<FilterTab, number> = {
    all:       schools.length,
    active:    schools.filter(s => s.subscription_status === "active").length,
    trial:     schools.filter(s => s.subscription_status === "trial").length,
    suspended: schools.filter(s => s.subscription_status === "suspended").length,
    expired:   schools.filter(s => ["expired", "cancelled"].includes(s.subscription_status)).length,
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manage Schools</h1>
          <p className="text-sm text-gray-500 mt-0.5">All registered schools and their subscriptions</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Filter tabs + search */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
          {(["all", "active", "trial", "suspended", "expired"] as FilterTab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
                filter === tab
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab} <span className="ml-1 opacity-60">({filterCounts[tab]})</span>
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search schools or admins…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 h-9 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-16 text-red-500 text-sm">{error}</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Building2 size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 text-sm">
              {search || filter !== "all" ? "No schools match your filters." : "No schools registered yet."}
            </p>
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
              {filtered.map(s => {
                const meta = STATUS_META[s.subscription_status] ?? STATUS_META.trial;
                const MetaIcon = meta.icon;
                const isBusy = actionId === s.id;
                const isSuspended = s.subscription_status === "suspended";
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
                      <span className="px-2 py-0.5 rounded-full text-xs font-semibold capitalize"
                        style={{ backgroundColor: `${PLAN_COLOR[s.plan]}15`, color: PLAN_COLOR[s.plan] }}>
                        {s.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <MetaIcon size={12} style={{ color: meta.color }} />
                        <span className="text-xs font-medium" style={{ color: meta.color }}>{meta.label}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{s.trial_ends ?? "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-gray-500 text-xs">
                        <Users size={12} /> {s.user_count}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{s.admin_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => { enter(s.id, s.name); navigate("/"); }}
                          disabled={isBusy}
                          className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors disabled:opacity-40"
                        >
                          <LogIn size={11} /> Enter
                        </button>
                        {isSuspended ? (
                          <button
                            onClick={() => handleActivate(s)}
                            disabled={isBusy}
                            title="Activate school"
                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-green-600 border border-green-200 rounded-lg hover:bg-green-50 transition-colors disabled:opacity-40"
                          >
                            <PlayCircle size={11} /> Activate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSuspend(s)}
                            disabled={isBusy}
                            title="Suspend school"
                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50 transition-colors disabled:opacity-40"
                          >
                            <PauseCircle size={11} /> Suspend
                          </button>
                        )}
                        <button
                          onClick={() => openModal(s)}
                          className="px-2.5 py-1.5 text-xs font-medium text-violet-600 border border-violet-200 rounded-lg hover:bg-violet-50 transition-colors"
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

      {/* Manage modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl w-full max-w-md mx-4 p-6">
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{modal.school.name}</h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  {modal.school.email ?? ""}{modal.school.contact_phone ? ` · ${modal.school.contact_phone}` : ""}
                </p>
              </div>
              <button onClick={() => setModal(null)} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={16} />
              </button>
            </div>

            {/* School info strip */}
            <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
              {[
                { label: "Admin",   value: modal.school.admin_name ?? "—" },
                { label: "Users",   value: String(modal.school.user_count) },
                { label: "Registered", value: modal.school.created_at?.slice(0, 10) ?? "—" },
                { label: "Current status", value: modal.school.subscription_status },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-gray-400 mb-0.5">{label}</p>
                  <p className="font-semibold text-gray-800 capitalize">{value}</p>
                </div>
              ))}
            </div>

            {saveError && (
              <div className="mb-4 px-3 py-2.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                {saveError}
              </div>
            )}

            {/* Subscription fields */}
            <div className="space-y-3 mb-5">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Plan</label>
                <select
                  value={modal.plan}
                  onChange={e => setModal(m => m && { ...m, plan: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {PLANS.map(p => (
                    <option key={p} value={p} className="capitalize">{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Status</label>
                <select
                  value={modal.status}
                  onChange={e => setModal(m => m && { ...m, status: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {STATUSES.map(s => (
                    <option key={s} value={s} className="capitalize">{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Trial / Expiry date</label>
                <input
                  type="date"
                  value={modal.trial_ends}
                  onChange={e => setModal(m => m && { ...m, trial_ends: e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                />
              </div>
            </div>

            {/* Danger zone */}
            <div className="border-t border-gray-100 pt-4 mb-5">
              <p className="text-xs font-semibold text-gray-500 mb-3">Support Actions</p>
              <div className="flex gap-2">
                <button
                  onClick={() => handleResetPassword(modal.school)}
                  disabled={actionId === modal.school.id}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-orange-600 border border-orange-200 rounded-lg hover:bg-orange-50 transition-colors disabled:opacity-50"
                >
                  <KeyRound size={12} /> Reset Admin Password
                </button>
                {modal.school.subscription_status === "suspended" ? (
                  <button
                    onClick={() => { handleActivate(modal.school); setModal(null); }}
                    disabled={actionId === modal.school.id}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-green-600 border border-green-200 rounded-lg hover:bg-green-50 transition-colors disabled:opacity-50"
                  >
                    <PlayCircle size={12} /> Activate
                  </button>
                ) : (
                  <button
                    onClick={() => { handleSuspend(modal.school); setModal(null); }}
                    disabled={actionId === modal.school.id}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50 transition-colors disabled:opacity-50"
                  >
                    <PauseCircle size={12} /> Suspend School
                  </button>
                )}
              </div>
            </div>

            <div className="flex gap-2.5">
              <button
                onClick={() => setModal(null)}
                className="flex-1 py-2.5 text-sm font-medium text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 py-2.5 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-60 rounded-xl transition-colors"
              >
                {saving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset password result modal */}
      {resetResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl w-full max-w-sm mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                <KeyRound size={18} className="text-orange-600" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-gray-900">Password Reset</h2>
                <p className="text-xs text-gray-500">{resetResult.schoolName}</p>
              </div>
            </div>

            <p className="text-xs text-gray-600 mb-3">
              A temporary password has been generated. Share it with the school admin.
              They will be forced to change it on first login.
            </p>

            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 mb-4">
              <code className="flex-1 text-sm font-mono text-gray-900 tracking-wide">
                {resetResult.password}
              </code>
              <button onClick={copyPassword} className="text-gray-400 hover:text-gray-700 transition-colors">
                {resetResult.copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
              </button>
            </div>

            <button
              onClick={() => setResetResult(null)}
              className="w-full py-2.5 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-xl transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
