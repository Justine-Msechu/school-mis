import { useState, useEffect, useCallback } from "react";
import { Users, Plus, Edit2, ToggleLeft, ToggleRight, Save, Star, CreditCard, CheckCircle, AlertTriangle, Clock, BookOpen, KeyRound } from "lucide-react";
import { getUsers, getRoles, createUser, updateUser, toggleUserActive, resetUserPassword, getConfig, setConfig, getAcademicYears, createAcademicYear, setCurrentYear, type AppUser, type Role, type AcademicYear } from "@/api/settings";
import { getTeachers, type Teacher } from "@/api/teachers";
import { getSubscriptionStatus, activateSubscription, type SubscriptionInfo } from "@/api/subscription";
import { getSubjects, createSubject, updateSubject, toggleSubject, type Subject } from "@/api/subjects";
import { listPortalAccounts, createStudentAccount, createParentAccount, deletePortalAccount, type PortalAccounts } from "@/api/portal";
import { getStudents } from "@/api/students";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "users" | "school" | "years" | "subscription" | "subjects" | "portal";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function RoleBadge({ label, color }: { label: string; color: string }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ background: color + "22", color }}>
      {label}
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

// ── User form ───────────────────────────────────────────────────────────────

const TEACHER_ROLES = new Set(["class_teacher", "subject_teacher"]);

function UserForm({ roles, teachers, initial, onSave, onCancel }: {
  roles: Role[];
  teachers: Teacher[];
  initial?: AppUser;
  onSave: (data: any) => Promise<void>;
  onCancel: () => void;
}) {
  const [username, setUsername]   = useState(initial?.username || "");
  const [fullName, setFullName]   = useState(initial?.full_name || "");
  const [role, setRole]           = useState(initial?.role || roles[0]?.key || "");
  const [teacherId, setTeacherId] = useState<number | "">(
    (initial as any)?.teacher_id ?? ""
  );
  const [password, setPassword] = useState("");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  const needsTeacher = TEACHER_ROLES.has(role);

  const submit = async () => {
    setError("");
    if (!fullName.trim()) { setError("Full name is required."); return; }
    if (!initial && !username.trim()) { setError("Username is required."); return; }
    if (!initial && !password) { setError("Password is required for new users."); return; }
    if (password && password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setSaving(true);
    try {
      const payload: any = { full_name: fullName.trim(), role };
      if (!initial) payload.username = username.trim();
      if (password) payload.password = password;
      payload.teacher_id = teacherId !== "" ? teacherId : null;
      await onSave(payload);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save user.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit User" : "New User"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="flex flex-col gap-3">
          {!initial && (
            <Field label="Username">
              <input value={username} onChange={(e) => setUsername(e.target.value)} className={INPUT} />
            </Field>
          )}
          <Field label="Full Name">
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={INPUT} />
          </Field>
          <Field label="Role">
            <select value={role} onChange={(e) => setRole(e.target.value)} className={INPUT}>
              {roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
            </select>
          </Field>
          {needsTeacher && (
            <Field label="Linked Teacher Record">
              <select value={teacherId} onChange={(e) => setTeacherId(e.target.value ? Number(e.target.value) : "")} className={INPUT}>
                <option value="">— Not linked —</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.first_name} {t.last_name} ({t.employee_no || "no emp no"})</option>)}
              </select>
              <p className="text-2xs text-gray-400 mt-0.5">Link to a teacher so they can access their class and attendance data.</p>
            </Field>
          )}
          <Field label={`Password${initial ? " (leave blank to keep current)" : " *"}`}>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={INPUT} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

// ── School info tab ─────────────────────────────────────────────────────────

function SchoolInfoTab() {
  const [form, setForm] = useState({
    school_name:    "",
    school_address: "",
    school_phone:   "",
    school_email:   "",
    school_motto:   "",
    school_type:    "primary",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);

  useEffect(() => {
    getConfig().then((cfg) => {
      setForm({
        school_name:    cfg.school_name    || "",
        school_address: cfg.school_address || "",
        school_phone:   cfg.school_phone   || "",
        school_email:   cfg.school_email   || "",
        school_motto:   cfg.school_motto   || "",
        school_type:    cfg.school_type    || "primary",
      });
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      for (const [key, value] of Object.entries(form)) {
        await setConfig(key, value);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  };

  if (loading) return <div className="py-8 text-center text-sm text-gray-400">Loading…</div>;

  return (
    <div className="max-w-lg space-y-4">
      <Field label="School Name">
        <input className={INPUT} value={form.school_name} onChange={(e) => set("school_name", e.target.value)} />
      </Field>
      <Field label="Address">
        <input className={INPUT} value={form.school_address} onChange={(e) => set("school_address", e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Phone">
          <input className={INPUT} value={form.school_phone} onChange={(e) => set("school_phone", e.target.value)} />
        </Field>
        <Field label="Email">
          <input type="email" className={INPUT} value={form.school_email} onChange={(e) => set("school_email", e.target.value)} />
        </Field>
      </div>
      <Field label="Motto">
        <input className={INPUT} value={form.school_motto} onChange={(e) => set("school_motto", e.target.value)} />
      </Field>
      <Field label="School Type">
        <select className={INPUT} value={form.school_type} onChange={(e) => set("school_type", e.target.value)}>
          <option value="primary">Primary</option>
          <option value="secondary">Secondary</option>
          <option value="combined">Combined</option>
        </select>
      </Field>
      <div className="pt-2">
        <Button variant="primary" icon={<Save size={14} />} onClick={save} disabled={saving}>
          {saved ? "Saved!" : saving ? "Saving…" : "Save Changes"}
        </Button>
      </div>
    </div>
  );
}

// ── Academic years tab ──────────────────────────────────────────────────────

function AcademicYearDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({ label: "", start_date: "", end_date: "", is_current: false });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.label || !form.start_date || !form.end_date) { setError("All fields are required."); return; }
    setSaving(true); setError("");
    try {
      await createAcademicYear({ label: form.label, start_date: form.start_date, end_date: form.end_date, is_current: form.is_current });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to create year.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Add Academic Year</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Label *"><input className={INPUT} value={form.label} onChange={(e) => set("label", e.target.value)} placeholder="e.g. 2025/2026" /></Field>
          <Field label="Start Date *"><input type="date" className={INPUT} value={form.start_date} onChange={(e) => set("start_date", e.target.value)} /></Field>
          <Field label="End Date *"><input type="date" className={INPUT} value={form.end_date} onChange={(e) => set("end_date", e.target.value)} /></Field>
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" checked={form.is_current} onChange={(e) => set("is_current", e.target.checked)} className="rounded" />
            Set as current academic year
          </label>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Create"}</Button>
        </div>
      </div>
    </div>
  );
}

function AcademicYearsTab() {
  const [years, setYears]   = useState<AcademicYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getAcademicYears().then(setYears).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSetCurrent = async (id: number) => {
    await setCurrentYear(id).catch(() => {});
    load();
  };

  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Add Year</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Label</th>
              <th className="px-4 py-3">Start</th>
              <th className="px-4 py-3">End</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : years.length === 0
              ? <tr><td colSpan={5} className="py-12 text-center text-sm text-gray-400">No academic years yet</td></tr>
              : years.map((y) => (
                <tr key={y.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{y.label}</td>
                  <td className="px-4 py-3 text-gray-600">{y.start_date}</td>
                  <td className="px-4 py-3 text-gray-600">{y.end_date}</td>
                  <td className="px-4 py-3">
                    {y.is_current
                      ? <Badge variant="green">Current</Badge>
                      : <Badge variant="gray">Past</Badge>
                    }
                  </td>
                  <td className="px-4 py-3">
                    {!y.is_current && (
                      <Button variant="outline" size="sm" icon={<Star size={12} />} onClick={() => handleSetCurrent(y.id)}>
                        Set Current
                      </Button>
                    )}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && (
        <AcademicYearDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

// ── Subscription tab ────────────────────────────────────────────────────────

const PLAN_FEATURES: Record<string, string[]> = {
  trial:    ["Up to 50 users", "All modules included", "30-day free trial", "Email support"],
  standard: ["Up to 150 users", "All modules included", "Priority support", "Data export"],
  premium:  ["Up to 500 users", "All modules included", "Dedicated support", "Custom branding", "API access"],
  lifetime: ["Unlimited users", "All modules included", "Lifetime updates", "Priority support", "Custom branding"],
};

function SubscriptionTab() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";
  const [info, setInfo]       = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [newPlan, setNewPlan] = useState("standard");
  const [trialDays, setTrialDays] = useState("30");
  const [saved, setSaved]     = useState(false);
  const [error, setError]     = useState("");

  useEffect(() => {
    getSubscriptionStatus().then(setInfo).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const activate = async () => {
    setActivating(true); setError(""); setSaved(false);
    try {
      let trialEnds: string | undefined;
      if (newPlan === "trial") {
        const d = new Date();
        d.setDate(d.getDate() + parseInt(trialDays || "30"));
        trialEnds = d.toISOString().slice(0, 10);
      }
      await activateSubscription(newPlan, undefined, trialEnds);
      const fresh = await getSubscriptionStatus();
      setInfo(fresh);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to update subscription.");
    } finally { setActivating(false); }
  };

  if (loading) return <div className="py-8 text-center text-sm text-gray-400">Loading…</div>;
  if (!info) return null;

  const statusIcon =
    info.status === "expired"   ? <AlertTriangle size={18} className="text-red-500" /> :
    info.status === "trial"     ? <Clock size={18} className="text-amber-500" /> :
    <CheckCircle size={18} className="text-green-500" />;

  return (
    <div className="max-w-2xl space-y-6">
      {/* Current plan card */}
      <div className="rounded-xl border-2 p-5" style={{ borderColor: info.plan_color + "60", background: info.plan_color + "08" }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              {statusIcon}
              <span className="text-sm font-semibold text-gray-700">Current Plan</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: info.plan_color }}>{info.plan_label}</p>
            {info.school_name && <p className="text-sm text-gray-500 mt-0.5">{info.school_name}</p>}
          </div>
          <div className="text-right">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
              info.status === "expired" ? "bg-red-100 text-red-700" :
              info.status === "trial"   ? "bg-amber-100 text-amber-700" :
              "bg-green-100 text-green-700"
            }`}>
              {info.status === "trial" ? `Trial${info.days_left !== null ? ` — ${info.days_left}d left` : ""}` :
               info.status === "expired" ? "Expired" : "Active"}
            </span>
            {info.trial_ends && (
              <p className="text-xs text-gray-400 mt-1">
                {info.status === "expired" ? "Expired" : "Expires"}: {info.trial_ends}
              </p>
            )}
            <p className="text-xs text-gray-400 mt-0.5">Max {info.max_users} users</p>
          </div>
        </div>
        {info.warning && (
          <div className="mt-3 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            {info.warning}
          </div>
        )}
        {/* Features */}
        <div className="mt-4 flex flex-wrap gap-2">
          {(PLAN_FEATURES[info.plan] ?? []).map((f) => (
            <span key={f} className="flex items-center gap-1 text-xs text-gray-600 bg-white border border-gray-200 px-2.5 py-1 rounded-full">
              <CheckCircle size={11} className="text-green-500" /> {f}
            </span>
          ))}
        </div>
      </div>

      {/* Admin: upgrade / change plan */}
      {isAdmin && (
        <div className="rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <CreditCard size={16} className="text-gray-400" /> Change Subscription Plan
          </h3>
          {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {(["trial","standard","premium","lifetime"] as const).map((p) => (
              <button key={p} onClick={() => setNewPlan(p)}
                className={`p-3 rounded-xl border-2 text-left transition-all ${newPlan === p ? "border-violet-500 bg-violet-50" : "border-gray-200 hover:border-gray-300"}`}>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">{p}</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 capitalize">
                  {p === "trial" ? "Free Trial" : p === "lifetime" ? "Lifetime" : p.charAt(0).toUpperCase() + p.slice(1)}
                </p>
              </button>
            ))}
          </div>
          {newPlan === "trial" && (
            <div className="mb-4 flex items-center gap-3">
              <label className="text-xs font-medium text-gray-600 whitespace-nowrap">Trial duration (days)</label>
              <input type="number" min="1" max="365" value={trialDays} onChange={(e) => setTrialDays(e.target.value)}
                className="w-20 h-8 px-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          )}
          <Button variant="primary" icon={<Save size={14} />} onClick={activate} disabled={activating}>
            {saved ? "Plan Updated!" : activating ? "Updating…" : "Apply Plan"}
          </Button>
          <p className="text-xs text-gray-400 mt-3">
            Changes take effect immediately. For billing questions contact your system vendor.
          </p>
        </div>
      )}

      {/* Plan comparison table */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">Plan Comparison</h3>
        </div>
        <div className="table-scroll">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 font-semibold">
              <th className="px-4 py-2.5 text-left">Feature</th>
              {["Trial","Standard","Premium","Lifetime"].map((p) => (
                <th key={p} className="px-4 py-2.5 text-center">{p}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {[
              ["Max users",       "50", "150", "500", "∞"],
              ["All modules",     "✓", "✓", "✓", "✓"],
              ["Email support",   "✓", "✓", "✓", "✓"],
              ["Priority support","—", "✓", "✓", "✓"],
              ["Custom branding", "—", "—", "✓", "✓"],
              ["API access",      "—", "—", "✓", "✓"],
              ["Duration",        "30 days","Monthly","Monthly","Forever"],
            ].map(([feat, ...vals]) => (
              <tr key={feat} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 text-gray-700 font-medium">{feat}</td>
                {vals.map((v, i) => (
                  <td key={i} className={`px-4 py-2.5 text-center ${v === "✓" ? "text-green-600" : v === "—" ? "text-gray-300" : "text-gray-700"}`}>
                    {v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}

// ── Subjects tab ────────────────────────────────────────────────────────────

function SubjectForm({ initial, onSave, onCancel }: {
  initial?: Subject;
  onSave: (data: any) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName]               = useState(initial?.name || "");
  const [code, setCode]               = useState(initial?.code || "");
  const [gradeLevel, setGradeLevel]   = useState<string>(initial?.grade_level?.toString() || "");
  const [subjectType, setSubjectType] = useState(initial?.subject_type || "compulsory");
  const [creditHours, setCreditHours] = useState(initial?.credit_hours?.toString() || "1");
  const [saving, setSaving]           = useState(false);
  const [error, setError]             = useState("");

  const submit = async () => {
    setError("");
    if (!name.trim()) { setError("Subject name is required."); return; }
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        code: code.trim() || undefined,
        grade_level: gradeLevel ? parseInt(gradeLevel) : null,
        subject_type: subjectType,
        credit_hours: parseInt(creditHours) || 1,
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save subject.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Subject" : "New Subject"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="flex flex-col gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Subject Name *</label>
            <input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Mathematics" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Code</label>
              <input className={INPUT} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. MATH" maxLength={10} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Grade Level</label>
              <input className={INPUT} type="number" min={1} max={13} value={gradeLevel} onChange={(e) => setGradeLevel(e.target.value)} placeholder="All grades" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
              <select className={INPUT} value={subjectType} onChange={(e) => setSubjectType(e.target.value)}>
                <option value="compulsory">Compulsory</option>
                <option value="elective">Elective</option>
                <option value="optional">Optional</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Credit Hours</label>
              <input className={INPUT} type="number" min={1} max={10} value={creditHours} onChange={(e) => setCreditHours(e.target.value)} />
            </div>
          </div>
        </div>
        <div className="flex gap-2 mt-5 justify-end">
          <button onClick={onCancel} className="h-9 px-4 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
          <button onClick={submit} disabled={saving} className="h-9 px-5 bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg">
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function SubjectsTab() {
  const [subjects, setSubjects]   = useState<Subject[]>([]);
  const [loading, setLoading]     = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [editSubject, setEditSubject]   = useState<Subject | null | "new">(null);

  const load = useCallback(() => {
    setLoading(true);
    getSubjects(showInactive).then(setSubjects).catch(() => {}).finally(() => setLoading(false));
  }, [showInactive]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (data: any) => {
    if (editSubject === "new") await createSubject(data);
    else if (editSubject)      await updateSubject(editSubject.id, data);
    setEditSubject(null);
    load();
  };

  const handleToggle = async (id: number) => {
    await toggleSubject(id).catch(() => {});
    load();
  };

  const TYPE_COLOR: Record<string, string> = {
    compulsory: "bg-blue-50 text-blue-700",
    elective:   "bg-purple-50 text-purple-700",
    optional:   "bg-gray-100 text-gray-600",
  };

  return (
    <div>
      {editSubject !== null && (
        <SubjectForm
          initial={editSubject === "new" ? undefined : editSubject}
          onSave={handleSave}
          onCancel={() => setEditSubject(null)}
        />
      )}
      <div className="flex items-center justify-between mb-4">
        <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer select-none">
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="rounded" />
          Show inactive subjects
        </label>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setEditSubject("new")}>
          Add Subject
        </Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Subject</th>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Grade Level</th>
                <th className="px-4 py-3">Credits</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
                : subjects.length === 0
                ? <tr><td colSpan={7} className="py-16"><EmptyState icon={BookOpen} title="No subjects yet" description="Add the subjects taught at your school" /></td></tr>
                : subjects.map((s) => (
                  <tr key={s.id} className={`hover:bg-gray-50 transition-colors ${!s.is_active ? "opacity-50" : ""}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.code || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${TYPE_COLOR[s.subject_type] || "bg-gray-100 text-gray-600"}`}>
                        {s.subject_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.grade_level ? `Grade ${s.grade_level}` : "All grades"}</td>
                    <td className="px-4 py-3 text-gray-500">{s.credit_hours}</td>
                    <td className="px-4 py-3">
                      {s.is_active ? <Badge variant="green">Active</Badge> : <Badge variant="red">Inactive</Badge>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setEditSubject(s)} className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors">
                          <Edit2 size={14} />
                        </button>
                        <button onClick={() => handleToggle(s.id)} className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors" title={s.is_active ? "Deactivate" : "Activate"}>
                          {s.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Portal Accounts tab ──────────────────────────────────────────────────────

type PortalForm = { student_id: string; username: string; password: string; full_name: string; relation: string };
const EMPTY_FORM: PortalForm = { student_id: "", username: "", password: "", full_name: "", relation: "Parent" };

function PortalAccountsTab() {
  const [data, setData]           = useState<PortalAccounts | null>(null);
  const [students, setStudents]   = useState<{ id: number; first_name: string; last_name: string; admission_no: string }[]>([]);
  const [form, setForm]           = useState<PortalForm>(EMPTY_FORM);
  const [mode, setMode]           = useState<"student" | "parent">("student");
  const [showForm, setShowForm]   = useState(false);
  const [saving, setSaving]       = useState(false);
  const [err, setErr]             = useState("");
  const [resetTarget, setResetTarget] = useState<{ id: number; name: string } | null>(null);
  const [resetPw, setResetPw]     = useState("");
  const [resetErr, setResetErr]   = useState("");
  const [resetSaving, setResetSaving] = useState(false);

  const load = () => listPortalAccounts().then(setData).catch(() => {});

  useEffect(() => {
    load();
    getStudents({}).then(r => setStudents(r.items)).catch(() => {});
  }, []);

  const set = (k: keyof PortalForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const handleCreate = async () => {
    if (!form.student_id || !form.username || !form.password || !form.full_name) {
      setErr("All fields are required."); return;
    }
    setSaving(true); setErr("");
    try {
      if (mode === "student") {
        await createStudentAccount({ student_id: +form.student_id, username: form.username, password: form.password, full_name: form.full_name });
      } else {
        await createParentAccount({ student_id: +form.student_id, username: form.username, password: form.password, full_name: form.full_name, relation: form.relation });
      }
      setForm(EMPTY_FORM); setShowForm(false); load();
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? "Failed to create account.");
    } finally { setSaving(false); }
  };

  const handleDelete = async (userId: number) => {
    if (!confirm("Delete this portal account? The user will no longer be able to log in.")) return;
    await deletePortalAccount(userId).catch(() => {});
    load();
  };

  const handlePortalReset = async () => {
    if (!resetTarget) return;
    if (resetPw.length < 6) { setResetErr("Password must be at least 6 characters."); return; }
    setResetSaving(true); setResetErr("");
    try {
      await resetUserPassword(resetTarget.id, resetPw);
      setResetTarget(null); setResetPw("");
    } catch (e: any) {
      setResetErr(e?.response?.data?.detail ?? "Failed to reset password.");
    } finally { setResetSaving(false); }
  };

  const studentOptions = students.map(s => ({ value: s.id, label: `${s.first_name} ${s.last_name} (${s.admission_no})` }));

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => { setShowForm(o => !o); setErr(""); }}>
          New Portal Account
        </Button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Create Portal Account</h3>
          <div className="flex gap-2">
            {(["student", "parent"] as const).map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${mode === m ? "bg-violet-600 text-white border-violet-600" : "border-gray-200 text-gray-600 hover:border-violet-300"}`}>
                {m === "student" ? "Student Account" : "Parent Account"}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Student *</label>
              <select value={form.student_id} onChange={set("student_id")} className={INPUT}>
                <option value="">Select student…</option>
                {studentOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Full Name *</label>
              <input className={INPUT} value={form.full_name} onChange={set("full_name")} placeholder={mode === "student" ? "Student's full name" : "Parent/Guardian name"} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Username *</label>
              <input className={INPUT} value={form.username} onChange={set("username")} placeholder="Login username" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Password *</label>
              <input className={INPUT} type="password" value={form.password} onChange={set("password")} placeholder="Min. 6 characters" />
            </div>
            {mode === "parent" && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Relation</label>
                <select value={form.relation} onChange={set("relation")} className={INPUT}>
                  {["Parent", "Mother", "Father", "Guardian", "Uncle", "Aunt", "Grandparent", "Sibling"].map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          {err && <p className="text-red-500 text-sm">{err}</p>}
          <div className="flex gap-2 justify-end pt-1">
            <button onClick={() => { setShowForm(false); setErr(""); }} className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
            <Button variant="primary" onClick={handleCreate} disabled={saving}>{saving ? "Creating…" : "Create Account"}</Button>
          </div>
        </div>
      )}

      {/* Student accounts */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Student Accounts ({data?.student_accounts.length ?? 0})</h3>
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Adm. No</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!data
                ? <tr><td colSpan={4} className="py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
                : data.student_accounts.length === 0
                ? <tr><td colSpan={4} className="py-8 text-center text-gray-400 text-sm">No student portal accounts yet.</td></tr>
                : data.student_accounts.map(a => (
                  <tr key={a.user_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{a.student_name}</td>
                    <td className="px-4 py-3 text-gray-500">{a.admission_no}</td>
                    <td className="px-4 py-3 text-gray-500">@{a.username}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex gap-1 justify-end">
                        <button onClick={() => { setResetTarget({ id: a.user_id, name: a.full_name || a.student_name }); setResetPw(""); setResetErr(""); }} className="text-xs text-blue-500 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50">Reset PW</button>
                        <button onClick={() => handleDelete(a.user_id)} className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50">Remove</button>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>

      {/* Parent accounts */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Parent Accounts ({data?.parent_accounts.length ?? 0})</h3>
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3">Parent Name</th>
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Relation</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!data
                ? <tr><td colSpan={5} className="py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
                : data.parent_accounts.length === 0
                ? <tr><td colSpan={5} className="py-8 text-center text-gray-400 text-sm">No parent portal accounts yet.</td></tr>
                : data.parent_accounts.map(a => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{a.full_name}</td>
                    <td className="px-4 py-3 text-gray-500">{a.student_name} ({a.admission_no})</td>
                    <td className="px-4 py-3 text-gray-500">{a.relation}</td>
                    <td className="px-4 py-3 text-gray-500">@{a.username}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex gap-1 justify-end">
                        <button onClick={() => { setResetTarget({ id: a.user_id, name: a.full_name || a.student_name }); setResetPw(""); setResetErr(""); }} className="text-xs text-blue-500 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50">Reset PW</button>
                        <button onClick={() => handleDelete(a.user_id)} className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50">Remove</button>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>

      {resetTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <KeyRound size={16} className="text-blue-600" /> Reset Password
            </h3>
            <p className="text-sm text-gray-500">
              Setting a new password for <strong>{resetTarget.name}</strong>.
              They will be required to change it on next login.
            </p>
            <div>
              <label className="block text-xs text-gray-500 mb-1">New temporary password</label>
              <input type="text" className={INPUT} value={resetPw} onChange={e => setResetPw(e.target.value)}
                placeholder="Min. 6 characters" autoFocus />
            </div>
            {resetErr && <p className="text-red-500 text-sm">{resetErr}</p>}
            <div className="flex gap-2 justify-end pt-1">
              <button onClick={() => setResetTarget(null)} className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
              <Button variant="primary" onClick={handlePortalReset} disabled={resetSaving}>
                {resetSaving ? "Saving…" : "Reset Password"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { can } = useAuthStore();
  const canAllUsers    = can("settings.users.manage");
  const canTeachers    = can("settings.teachers.manage");
  const canSchool      = can("settings.school.manage");
  const canYears       = can("settings.years.manage") || canAllUsers;
  const canUsers       = canAllUsers || canTeachers;
  const canSubjects    = canAllUsers || can("settings.school.manage");

  const defaultTab: Tab = canUsers ? "users" : canSchool ? "school" : "years";

  const [tab, setTab]       = useState<Tab>(defaultTab);
  const [users, setUsers]   = useState<AppUser[]>([]);
  const [roles, setRoles]   = useState<Role[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [editUser, setEditUser]       = useState<AppUser | null | "new">(null);
  const [resetUser, setResetUser]     = useState<AppUser | null>(null);
  const [resetPw, setResetPw]         = useState("");
  const [resetSaving, setResetSaving] = useState(false);
  const [resetErr, setResetErr]       = useState("");

  useEffect(() => {
    getTeachers("").then(setTeachers).catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    Promise.all([getUsers(), getRoles()])
      .then(([u, r]) => { setUsers(u); setRoles(r); })
      .catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { if (tab === "users") load(); else setLoading(false); }, [tab]);

  const handleSave = async (data: any) => {
    if (editUser === "new") await createUser(data);
    else if (editUser)      await updateUser(editUser.id, data);
    setEditUser(null);
    load();
  };

  const handleToggle = async (id: number) => {
    await toggleUserActive(id).catch(() => {});
    load();
  };

  const handleReset = async () => {
    if (!resetUser) return;
    if (resetPw.length < 6) { setResetErr("Password must be at least 6 characters."); return; }
    setResetSaving(true); setResetErr("");
    try {
      await resetUserPassword(resetUser.id, resetPw);
      setResetUser(null); setResetPw("");
    } catch (e: any) {
      setResetErr(e?.response?.data?.detail ?? "Failed to reset password.");
    } finally { setResetSaving(false); }
  };

  const roleMap = Object.fromEntries(roles.map((r) => [r.key, r]));

  const TABS = [
    canUsers    && { key: "users"        as Tab, label: canAllUsers ? "Users" : "Teacher Accounts" },
    canSchool   && { key: "school"       as Tab, label: "School Info" },
    canYears    && { key: "years"        as Tab, label: "Academic Years" },
    canSubjects && { key: "subjects"     as Tab, label: "Subjects" },
    canAllUsers && { key: "portal"       as Tab, label: "Portal Accounts" },
    canSchool   && { key: "subscription" as Tab, label: "Subscription" },
  ].filter(Boolean) as Array<{ key: Tab; label: string }>;

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {canAllUsers ? "Users, school info and academic year configuration" : "Teacher accounts and academic calendar"}
          </p>
        </div>
        {tab === "users" && canUsers && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setEditUser("new")}>
            {canAllUsers ? "Add User" : "Add Teacher Account"}
          </Button>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "users" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="table-scroll"><table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
                : users.length === 0
                ? <tr><td colSpan={5} className="py-16"><EmptyState icon={Users} title="No users found" /></td></tr>
                : users.map((u) => {
                  const role = roleMap[u.role];
                  return (
                    <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                      <td className="px-4 py-3 text-gray-500">@{u.username}</td>
                      <td className="px-4 py-3">
                        {role
                          ? <RoleBadge label={role.label} color={role.color} />
                          : <span className="text-gray-400 text-xs">{u.role}</span>
                        }
                      </td>
                      <td className="px-4 py-3">
                        {u.is_active ? <Badge variant="green">Active</Badge> : <Badge variant="red">Inactive</Badge>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button onClick={() => setEditUser(u)} className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors" title="Edit">
                            <Edit2 size={14} />
                          </button>
                          {canAllUsers && (
                            <button onClick={() => { setResetUser(u); setResetPw(""); setResetErr(""); }} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Reset password">
                              <KeyRound size={14} />
                            </button>
                          )}
                          <button onClick={() => handleToggle(u.id)} className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors" title="Toggle active">
                            {u.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table></div>
        </div>
      )}

      {tab === "school"        && <SchoolInfoTab />}
      {tab === "years"         && <AcademicYearsTab />}
      {tab === "subjects"      && <SubjectsTab />}
      {tab === "portal"        && <PortalAccountsTab />}
      {tab === "subscription"  && <SubscriptionTab />}

      {resetUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <KeyRound size={16} className="text-blue-600" /> Reset Password
            </h3>
            <p className="text-sm text-gray-500">
              Setting a new password for <strong>{resetUser.full_name}</strong> (@{resetUser.username}).
              They will be required to change it on next login.
            </p>
            <div>
              <label className="block text-xs text-gray-500 mb-1">New temporary password</label>
              <input
                type="text"
                className={INPUT}
                value={resetPw}
                onChange={e => setResetPw(e.target.value)}
                placeholder="Min. 6 characters"
                autoFocus
              />
            </div>
            {resetErr && <p className="text-red-500 text-sm">{resetErr}</p>}
            <div className="flex gap-2 justify-end pt-1">
              <button onClick={() => setResetUser(null)} className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
              <Button variant="primary" onClick={handleReset} disabled={resetSaving}>
                {resetSaving ? "Saving…" : "Reset Password"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {editUser !== null && (
        <UserForm
          roles={roles}
          teachers={teachers}
          initial={editUser === "new" ? undefined : editUser}
          onSave={handleSave as (data: any) => Promise<void>}
          onCancel={() => setEditUser(null)}
        />
      )}
    </div>
  );
}
