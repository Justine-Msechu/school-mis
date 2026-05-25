import { useState, useEffect, useCallback } from "react";
import { Users, Plus, Edit2, ToggleLeft, ToggleRight, Save, Star } from "lucide-react";
import { getUsers, getRoles, createUser, updateUser, toggleUserActive, getConfig, setConfig, getAcademicYears, createAcademicYear, setCurrentYear, type AppUser, type Role, type AcademicYear } from "@/api/settings";
import { getTeachers, type Teacher } from "@/api/teachers";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "users" | "school" | "years";

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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
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
        <table className="w-full text-sm">
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
        </table>
      </div>
      {dialog && (
        <AcademicYearDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [tab, setTab]       = useState<Tab>("users");
  const [users, setUsers]   = useState<AppUser[]>([]);
  const [roles, setRoles]   = useState<Role[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [editUser, setEditUser] = useState<AppUser | null | "new">(null);

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

  const roleMap = Object.fromEntries(roles.map((r) => [r.key, r]));

  const TABS = [
    { key: "users"  as Tab, label: "Users" },
    { key: "school" as Tab, label: "School Info" },
    { key: "years"  as Tab, label: "Academic Years" },
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500 mt-0.5">Users, school info and academic year configuration</p>
        </div>
        {tab === "users" && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setEditUser("new")}>Add User</Button>
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
          <table className="w-full text-sm">
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
                          <button onClick={() => setEditUser(u)} className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors">
                            <Edit2 size={14} />
                          </button>
                          <button onClick={() => handleToggle(u.id)} className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors">
                            {u.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}

      {tab === "school" && <SchoolInfoTab />}
      {tab === "years"  && <AcademicYearsTab />}

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
