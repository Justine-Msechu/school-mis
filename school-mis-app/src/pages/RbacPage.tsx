import { useState, useEffect, useCallback } from "react";
import { ShieldCheck, Plus, Trash2, Save, RefreshCw, UserCheck, Users } from "lucide-react";
import {
  getRbacRoles, listPermissions, setRolePermissions,
  listTeacherAssignments, assignTeacher, removeTeacherAssignment,
  listClassTeacherAssignments, assignClassTeacher, removeClassTeacherAssignment,
  getUserOverrides, addUserOverride, deleteUserOverride,
  type RbacRole, type Permission, type TeacherAssignment,
  type ClassTeacherAssignment, type PermissionOverride,
} from "@/api/rbac";
import { getUsers, type AppUser } from "@/api/settings";
import { getClassList, type ClassRecord } from "@/api/classes";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "roles" | "assignments" | "overrides";

const INPUT =
  "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";
const SELECT =
  "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

// ── Subject interface (minimal) ────────────────────────────────────────────────
interface Subject { id: number; name: string; code: string | null }

function useSubjects() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  useEffect(() => {
    api.get<Subject[]>("/classes/subjects").catch(() =>
      api.get<Subject[]>("/subjects")
    ).then((r) => setSubjects(r.data)).catch(() => {});
  }, []);
  return subjects;
}

// ── Tab: Roles & Permissions ──────────────────────────────────────────────────

function RolesTab() {
  const { can } = useAuthStore();
  const canManage = can("settings.roles.manage");

  const [roles, setRoles]     = useState<RbacRole[]>([]);
  const [perms, setPerms]     = useState<Permission[]>([]);
  const [selected, setSelected] = useState<RbacRole | null>(null);
  const [rolePerms, setRolePerms] = useState<Set<string>>(new Set());
  const [loading, setLoading]   = useState(true);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getRbacRoles(), listPermissions()])
      .then(([r, p]) => { setRoles(r); setPerms(p); })
      .catch(() => setError("Failed to load roles"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  function selectRole(role: RbacRole) {
    setSelected(role);
    setRolePerms(new Set(role.permissions));
  }

  function togglePerm(code: string) {
    setRolePerms((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  }

  async function savePerms() {
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      await setRolePermissions(selected.id, [...rolePerms]);
      await load();
      setSelected((prev) => roles.find((r) => r.id === prev?.id) ?? prev);
    } catch {
      setError("Failed to save permissions");
    } finally {
      setSaving(false);
    }
  }

  // Group permissions by domain
  const domains = [...new Set(perms.map((p) => p.domain))].sort();

  if (loading) return <div className="p-6"><SkeletonRow /></div>;

  return (
    <div className="flex gap-4 h-full">
      {/* Left: role list */}
      <div className="w-56 flex-shrink-0 border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Roles</span>
        </div>
        <div className="overflow-y-auto">
          {roles.map((role) => (
            <button
              key={role.id}
              onClick={() => selectRole(role)}
              className={`w-full text-left px-3 py-2.5 text-sm border-b border-gray-100 transition-colors ${
                selected?.id === role.id
                  ? "bg-violet-50 text-violet-700 font-medium"
                  : "hover:bg-gray-50 text-gray-700"
              }`}
            >
              <span
                className="inline-block w-2 h-2 rounded-full mr-2"
                style={{ background: role.color }}
              />
              {role.label}
            </button>
          ))}
        </div>
      </div>

      {/* Right: permissions for selected role */}
      <div className="flex-1 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Select a role to view and edit permissions
          </div>
        ) : (
          <>
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <div>
                <span className="font-semibold text-gray-800">{selected.label}</span>
                <span className="ml-2 text-xs text-gray-500">
                  {rolePerms.size} permission{rolePerms.size !== 1 ? "s" : ""}
                </span>
              </div>
              {canManage && (
                <Button size="sm" onClick={savePerms} disabled={saving}>
                  <Save size={13} className="mr-1" />
                  {saving ? "Saving…" : "Save"}
                </Button>
              )}
            </div>
            {error && <p className="px-4 py-2 text-sm text-red-600">{error}</p>}
            <div className="overflow-y-auto flex-1 p-4 space-y-4">
              {domains.map((domain) => {
                const domainPerms = perms.filter((p) => p.domain === domain);
                return (
                  <div key={domain}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
                      {domain}
                    </p>
                    <div className="grid grid-cols-1 gap-1">
                      {domainPerms.map((p) => (
                        <label
                          key={p.code}
                          className="flex items-center gap-2 text-sm cursor-pointer group"
                        >
                          <input
                            type="checkbox"
                            checked={rolePerms.has(p.code)}
                            onChange={() => canManage && togglePerm(p.code)}
                            disabled={!canManage}
                            className="accent-violet-600 w-4 h-4"
                          />
                          <span className="font-mono text-xs text-violet-700 bg-violet-50 px-1.5 rounded">
                            {p.code}
                          </span>
                          <span className="text-gray-600 text-xs">{p.description}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Tab: Teacher Assignments ───────────────────────────────────────────────────

function AssignmentsTab() {
  const { can } = useAuthStore();
  const canManage = can("teachers.manage");

  const [subjectAssignments, setSubjectAssignments] = useState<TeacherAssignment[]>([]);
  const [classAssignments, setClassAssignments]     = useState<ClassTeacherAssignment[]>([]);
  const [users, setUsers]     = useState<AppUser[]>([]);
  const [classes, setClasses] = useState<ClassRecord[]>([]);
  const subjects = useSubjects();
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  // New subject assignment form
  const [sUserId, setSUserId]   = useState<number | "">("");
  const [sClassId, setSClassId] = useState<number | "">("");
  const [sSubjId, setSSubjId]   = useState<number | "">("");
  const [sAdding, setSAdding]   = useState(false);

  // New class teacher form
  const [ctUserId, setCtUserId]   = useState<number | "">("");
  const [ctClassId, setCtClassId] = useState<number | "">("");
  const [ctAdding, setCtAdding]   = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      listTeacherAssignments(),
      listClassTeacherAssignments(),
      getUsers(),
      getClassList(),
    ])
      .then(([sa, ca, u, c]) => {
        setSubjectAssignments(sa);
        setClassAssignments(ca);
        setUsers(u.filter((u) => ["class_teacher", "subject_teacher"].includes(u.role)));
        setClasses(c);
      })
      .catch(() => setError("Failed to load assignments"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function addSubjectAssignment() {
    if (!sUserId || !sClassId || !sSubjId) return;
    setSAdding(true);
    setError("");
    try {
      await assignTeacher({ user_id: +sUserId, class_id: +sClassId, subject_id: +sSubjId });
      setSUserId(""); setSClassId(""); setSSubjId("");
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add assignment");
    } finally {
      setSAdding(false);
    }
  }

  async function removeSubj(id: number) {
    setError("");
    try { await removeTeacherAssignment(id); await load(); }
    catch { setError("Failed to remove assignment"); }
  }

  async function addClassTeacher() {
    if (!ctUserId || !ctClassId) return;
    setCtAdding(true);
    setError("");
    try {
      await assignClassTeacher({ user_id: +ctUserId, class_id: +ctClassId });
      setCtUserId(""); setCtClassId("");
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add assignment");
    } finally {
      setCtAdding(false);
    }
  }

  async function removeCT(id: number) {
    setError("");
    try { await removeClassTeacherAssignment(id); await load(); }
    catch { setError("Failed to remove assignment"); }
  }

  if (loading) return <div className="p-6"><SkeletonRow /></div>;

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Subject assignments */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800 text-sm">Subject Assignments</h3>
          <p className="text-xs text-gray-500 mt-0.5">Assign a teacher to a class + subject pair</p>
        </div>

        {canManage && (
          <div className="p-4 border-b border-gray-200 bg-white">
            <div className="flex gap-2 flex-wrap">
              <Field label="Teacher">
                <select className={SELECT} value={sUserId} onChange={(e) => setSUserId(+e.target.value || "")}>
                  <option value="">Select teacher…</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Class">
                <select className={SELECT} value={sClassId} onChange={(e) => setSClassId(+e.target.value || "")}>
                  <option value="">Select class…</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Subject">
                <select className={SELECT} value={sSubjId} onChange={(e) => setSSubjId(+e.target.value || "")}>
                  <option value="">Select subject…</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </Field>
              <div className="flex items-end">
                <Button size="sm" onClick={addSubjectAssignment} disabled={sAdding || !sUserId || !sClassId || !sSubjId}>
                  <Plus size={13} className="mr-1" />
                  {sAdding ? "Adding…" : "Assign"}
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Teacher", "Class", "Subject", "Assigned"].map((h) => (
                  <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
                {canManage && <th />}
              </tr>
            </thead>
            <tbody>
              {subjectAssignments.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-gray-400 text-sm">No assignments yet</td></tr>
              ) : (
                subjectAssignments.map((a) => (
                  <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{a.teacher_name}</td>
                    <td className="px-4 py-2">{a.class_name}</td>
                    <td className="px-4 py-2">{a.subject_name}</td>
                    <td className="px-4 py-2 text-gray-500 text-xs">{a.assigned_at?.slice(0, 10)}</td>
                    {canManage && (
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => removeSubj(a.id)}
                          className="text-red-500 hover:text-red-700 p-1 rounded"
                          title="Remove assignment"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Class teacher assignments */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800 text-sm">Class Teacher Assignments</h3>
          <p className="text-xs text-gray-500 mt-0.5">Assign one teacher as responsible for a whole class</p>
        </div>

        {canManage && (
          <div className="p-4 border-b border-gray-200 bg-white">
            <div className="flex gap-2 flex-wrap">
              <Field label="Teacher">
                <select className={SELECT} value={ctUserId} onChange={(e) => setCtUserId(+e.target.value || "")}>
                  <option value="">Select teacher…</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Class">
                <select className={SELECT} value={ctClassId} onChange={(e) => setCtClassId(+e.target.value || "")}>
                  <option value="">Select class…</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </Field>
              <div className="flex items-end">
                <Button size="sm" onClick={addClassTeacher} disabled={ctAdding || !ctUserId || !ctClassId}>
                  <Plus size={13} className="mr-1" />
                  {ctAdding ? "Adding…" : "Assign"}
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Teacher", "Class", "Assigned"].map((h) => (
                  <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
                {canManage && <th />}
              </tr>
            </thead>
            <tbody>
              {classAssignments.length === 0 ? (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400 text-sm">No class teachers assigned yet</td></tr>
              ) : (
                classAssignments.map((a) => (
                  <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{a.teacher_name}</td>
                    <td className="px-4 py-2">{a.class_name}</td>
                    <td className="px-4 py-2 text-gray-500 text-xs">{a.assigned_at?.slice(0, 10)}</td>
                    {canManage && (
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => removeCT(a.id)}
                          className="text-red-500 hover:text-red-700 p-1 rounded"
                          title="Remove assignment"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Tab: User Overrides ────────────────────────────────────────────────────────

function OverridesTab() {
  const { can } = useAuthStore();
  const canManage = can("settings.users.manage");

  const [users, setUsers]       = useState<AppUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<AppUser | null>(null);
  const [overrides, setOverrides] = useState<PermissionOverride[]>([]);
  const [perms, setPerms]         = useState<Permission[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [search, setSearch]       = useState("");

  // New override form
  const [nPerm, setNPerm]       = useState("");
  const [nEffect, setNEffect]   = useState<"ALLOW" | "DENY">("ALLOW");
  const [nReason, setNReason]   = useState("");
  const [nExpiry, setNExpiry]   = useState("");
  const [adding, setAdding]     = useState(false);

  useEffect(() => {
    Promise.all([getUsers(), listPermissions()])
      .then(([u, p]) => { setUsers(u); setPerms(p); })
      .catch(() => setError("Failed to load data"));
  }, []);

  async function selectUser(u: AppUser) {
    setSelectedUser(u);
    setLoading(true);
    setError("");
    try {
      const res = await getUserOverrides(u.id);
      setOverrides(res.overrides);
    } catch {
      setError("Failed to load overrides");
    } finally {
      setLoading(false);
    }
  }

  async function addOverride() {
    if (!selectedUser || !nPerm) return;
    setAdding(true);
    setError("");
    try {
      await addUserOverride(selectedUser.id, {
        permission: nPerm,
        effect: nEffect,
        reason: nReason,
        expires_at: nExpiry || null,
      });
      setNPerm(""); setNReason(""); setNExpiry("");
      const res = await getUserOverrides(selectedUser.id);
      setOverrides(res.overrides);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add override");
    } finally {
      setAdding(false);
    }
  }

  async function removeOverride(oid: number) {
    if (!selectedUser) return;
    setError("");
    try {
      await deleteUserOverride(selectedUser.id, oid);
      const res = await getUserOverrides(selectedUser.id);
      setOverrides(res.overrides);
    } catch {
      setError("Failed to remove override");
    }
  }

  const filteredUsers = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.username.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex gap-4 h-full">
      {/* Left: user picker */}
      <div className="w-64 flex-shrink-0 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
          <input
            className={INPUT}
            placeholder="Search users…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="overflow-y-auto flex-1">
          {filteredUsers.map((u) => (
            <button
              key={u.id}
              onClick={() => selectUser(u)}
              className={`w-full text-left px-3 py-2.5 border-b border-gray-100 transition-colors ${
                selectedUser?.id === u.id
                  ? "bg-violet-50 text-violet-700"
                  : "hover:bg-gray-50 text-gray-700"
              }`}
            >
              <p className="text-sm font-medium truncate">{u.full_name}</p>
              <p className="text-xs text-gray-400">{u.username}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Right: overrides panel */}
      <div className="flex-1 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        {!selectedUser ? (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Select a user to view and manage permission overrides
          </div>
        ) : (
          <>
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
              <span className="font-semibold text-gray-800">{selectedUser.full_name}</span>
              <span className="ml-2 text-xs text-gray-400">{selectedUser.role}</span>
            </div>

            {error && <p className="px-4 py-2 text-sm text-red-600">{error}</p>}

            {/* Add override form */}
            {canManage && (
              <div className="p-4 border-b border-gray-200 bg-gray-50 space-y-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Add Override
                </p>
                <div className="flex gap-2 flex-wrap">
                  <Field label="Permission">
                    <select
                      className={SELECT}
                      value={nPerm}
                      onChange={(e) => setNPerm(e.target.value)}
                    >
                      <option value="">Select permission…</option>
                      {perms.map((p) => (
                        <option key={p.code} value={p.code}>{p.code}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Effect">
                    <select
                      className={SELECT}
                      value={nEffect}
                      onChange={(e) => setNEffect(e.target.value as "ALLOW" | "DENY")}
                    >
                      <option value="ALLOW">ALLOW</option>
                      <option value="DENY">DENY</option>
                    </select>
                  </Field>
                  <Field label="Reason">
                    <input
                      className={INPUT}
                      placeholder="Optional reason"
                      value={nReason}
                      onChange={(e) => setNReason(e.target.value)}
                    />
                  </Field>
                  <Field label="Expires (optional)">
                    <input
                      type="datetime-local"
                      className={INPUT}
                      value={nExpiry}
                      onChange={(e) => setNExpiry(e.target.value)}
                    />
                  </Field>
                  <div className="flex items-end">
                    <Button size="sm" onClick={addOverride} disabled={adding || !nPerm}>
                      <Plus size={13} className="mr-1" />
                      {adding ? "Adding…" : "Add"}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Overrides list */}
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="p-4"><SkeletonRow /></div>
              ) : overrides.length === 0 ? (
                <div className="flex items-center justify-center py-12 text-gray-400 text-sm">
                  No permission overrides for this user
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      {["Permission", "Effect", "Reason", "Expires", "Granted by", ""].map((h) => (
                        <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {overrides.map((ov) => (
                      <tr key={ov.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs text-violet-700">{ov.permission}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${
                              ov.effect === "ALLOW"
                                ? "bg-green-100 text-green-700"
                                : "bg-red-100 text-red-700"
                            }`}
                          >
                            {ov.effect}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs max-w-[160px] truncate">{ov.reason || "—"}</td>
                        <td className="px-4 py-2 text-gray-500 text-xs">
                          {ov.expires_at ? ov.expires_at.slice(0, 16).replace("T", " ") : "Permanent"}
                        </td>
                        <td className="px-4 py-2 text-gray-500 text-xs">{ov.granted_by_name ?? "—"}</td>
                        <td className="px-4 py-2 text-right">
                          {canManage && (
                            <button
                              onClick={() => removeOverride(ov.id)}
                              className="text-red-500 hover:text-red-700 p-1 rounded"
                              title="Remove override"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function RbacPage() {
  const { can } = useAuthStore();
  const [tab, setTab] = useState<Tab>("roles");

  // Determine which tabs to show
  const showRoles   = can("settings.roles.manage");
  const showAssign  = can("teachers.manage");
  const showOverrides = can("settings.users.manage");

  // Pick default visible tab
  const defaultTab: Tab = showRoles ? "roles" : showAssign ? "assignments" : "overrides";
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab);

  const tabs: { id: Tab; label: string; icon: React.ReactNode; visible: boolean }[] = [
    { id: "roles",       label: "Roles & Permissions", icon: <ShieldCheck size={15} />, visible: showRoles },
    { id: "assignments", label: "Teacher Assignments",  icon: <UserCheck size={15} />,  visible: showAssign },
    { id: "overrides",   label: "User Overrides",       icon: <Users size={15} />,       visible: showOverrides },
  ];

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-violet-100 flex items-center justify-center">
          <ShieldCheck size={18} className="text-violet-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">Roles & Access</h1>
          <p className="text-xs text-gray-500">Manage roles, permissions, teacher assignments and overrides</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-200 gap-0.5">
        {tabs.filter((t) => t.visible).map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === t.id
                ? "border-violet-600 text-violet-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "roles"       && <RolesTab />}
        {activeTab === "assignments" && <AssignmentsTab />}
        {activeTab === "overrides"   && <OverridesTab />}
      </div>
    </div>
  );
}
