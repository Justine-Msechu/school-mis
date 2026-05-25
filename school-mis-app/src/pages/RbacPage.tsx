import { useState, useEffect, useCallback } from "react";
import { ShieldCheck, Plus, Trash2, Save, Users, Key } from "lucide-react";
import {
  getRbacRoles, listPermissions, setRolePermissions,
  getUserOverrides, addUserOverride, deleteUserOverride,
  getUserRoles, setUserRoles,
  type RbacRole, type Permission, type PermissionOverride,
} from "@/api/rbac";
import { getUsers, type AppUser } from "@/api/settings";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "roles" | "userroles" | "overrides";

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

// ── Tab: Roles & Permissions ──────────────────────────────────────────────────

function RolesTab() {
  const { can } = useAuthStore();
  const canManage = can("settings.roles.manage");

  const [roles, setRoles]         = useState<RbacRole[]>([]);
  const [perms, setPerms]         = useState<Permission[]>([]);
  const [selected, setSelected]   = useState<RbacRole | null>(null);
  const [rolePerms, setRolePerms] = useState<Set<string>>(new Set());
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState("");

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
              <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ background: role.color }} />
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
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">{domain}</p>
                    <div className="grid grid-cols-1 gap-1">
                      {domainPerms.map((p) => (
                        <label key={p.code} className="flex items-center gap-2 text-sm cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={rolePerms.has(p.code)}
                            onChange={() => canManage && togglePerm(p.code)}
                            disabled={!canManage}
                            className="accent-violet-600 w-4 h-4"
                          />
                          <span className="font-mono text-xs text-violet-700 bg-violet-50 px-1.5 rounded">{p.code}</span>
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

// ── Tab: User Roles ───────────────────────────────────────────────────────────

function UserRolesTab() {
  const { can } = useAuthStore();
  const canManage = can("settings.users.manage");

  const [users, setUsers]           = useState<AppUser[]>([]);
  const [allRoles, setAllRoles]     = useState<RbacRole[]>([]);
  const [selectedUser, setSelectedUser] = useState<AppUser | null>(null);
  const [userRoles, setUserRoles_]  = useState<{ id: number; name: string; label: string; color: string }[]>([]);
  const [search, setSearch]         = useState("");
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [addRoleId, setAddRoleId]   = useState<number | "">("");
  const [saving, setSaving]         = useState(false);

  useEffect(() => {
    Promise.all([getUsers(), getRbacRoles()])
      .then(([u, r]) => { setUsers(u); setAllRoles(r); })
      .catch(() => setError("Failed to load data"));
  }, []);

  async function selectUser(u: AppUser) {
    setSelectedUser(u);
    setAddRoleId("");
    setLoading(true);
    setError("");
    try {
      const data = await getUserRoles(u.id);
      setUserRoles_(data.roles);
    } catch {
      setError("Failed to load user roles");
    } finally {
      setLoading(false);
    }
  }

  async function refreshRoles(uid: number) {
    const data = await getUserRoles(uid);
    setUserRoles_(data.roles);
  }

  async function addRole() {
    if (!selectedUser || !addRoleId) return;
    const newIds = [...userRoles.map((r) => r.id), +addRoleId];
    setSaving(true);
    setError("");
    try {
      await setUserRoles(selectedUser.id, newIds);
      await refreshRoles(selectedUser.id);
      setAddRoleId("");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add role");
    } finally {
      setSaving(false);
    }
  }

  async function removeRole(roleId: number) {
    if (!selectedUser) return;
    const newIds = userRoles.filter((r) => r.id !== roleId).map((r) => r.id);
    setSaving(true);
    setError("");
    try {
      await setUserRoles(selectedUser.id, newIds);
      await refreshRoles(selectedUser.id);
    } catch {
      setError("Failed to remove role");
    } finally {
      setSaving(false);
    }
  }

  const assignedIds    = new Set(userRoles.map((r) => r.id));
  const availableRoles = allRoles.filter((r) => !assignedIds.has(r.id));
  const filteredUsers  = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.username.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex gap-4 h-full">
      <div className="w-64 flex-shrink-0 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
          <input className={INPUT} placeholder="Search users…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="overflow-y-auto flex-1">
          {filteredUsers.map((u) => (
            <button
              key={u.id}
              onClick={() => selectUser(u)}
              className={`w-full text-left px-3 py-2.5 border-b border-gray-100 transition-colors ${
                selectedUser?.id === u.id ? "bg-violet-50 text-violet-700" : "hover:bg-gray-50 text-gray-700"
              }`}
            >
              <p className="text-sm font-medium truncate">{u.full_name}</p>
              <p className="text-xs text-gray-400">{u.username}</p>
            </button>
          ))}
          {filteredUsers.length === 0 && <p className="text-center py-6 text-sm text-gray-400">No users found</p>}
        </div>
      </div>

      <div className="flex-1 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        {!selectedUser ? (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Select a user to view and manage their roles
          </div>
        ) : (
          <>
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <div>
                <span className="font-semibold text-gray-800">{selectedUser.full_name}</span>
                <span className="ml-2 text-xs text-gray-400">{selectedUser.username}</span>
              </div>
              <span className="text-xs text-gray-500">{userRoles.length} role{userRoles.length !== 1 ? "s" : ""}</span>
            </div>

            {error && <p className="px-4 py-2 text-sm text-red-600">{error}</p>}

            {loading ? (
              <div className="p-4"><SkeletonRow /></div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
                  {userRoles.length === 0 ? (
                    <div className="flex items-center justify-center py-12 text-gray-400 text-sm">
                      No roles assigned to this user
                    </div>
                  ) : (
                    userRoles.map((role) => (
                      <div key={role.id} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                        <div className="flex items-center gap-3">
                          <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: role.color }} />
                          <div>
                            <p className="text-sm font-medium text-gray-800">{role.label}</p>
                            <p className="text-xs font-mono text-gray-400">{role.name}</p>
                          </div>
                        </div>
                        {canManage && (
                          <button
                            onClick={() => removeRole(role.id)}
                            disabled={saving}
                            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 transition-colors disabled:opacity-40"
                          >
                            <Trash2 size={13} /> Remove
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {canManage && (
                  <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-end gap-2">
                    <Field label="Add role">
                      <select
                        className={SELECT}
                        value={addRoleId}
                        onChange={(e) => setAddRoleId(+e.target.value || "")}
                        disabled={availableRoles.length === 0}
                      >
                        <option value="">
                          {availableRoles.length === 0 ? "All roles already assigned" : "Select role to add…"}
                        </option>
                        {availableRoles.map((r) => (
                          <option key={r.id} value={r.id}>{r.label}</option>
                        ))}
                      </select>
                    </Field>
                    <Button size="sm" onClick={addRole} disabled={!addRoleId || saving}>
                      <Plus size={13} className="mr-1" />
                      {saving ? "Saving…" : "Add"}
                    </Button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Tab: Permission Overrides ─────────────────────────────────────────────────

function OverridesTab() {
  const { can } = useAuthStore();
  const canManage = can("settings.users.manage");

  const [users, setUsers]           = useState<AppUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<AppUser | null>(null);
  const [overrides, setOverrides]   = useState<PermissionOverride[]>([]);
  const [perms, setPerms]           = useState<Permission[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [search, setSearch]         = useState("");
  const [nPerm, setNPerm]           = useState("");
  const [nEffect, setNEffect]       = useState<"ALLOW" | "DENY">("ALLOW");
  const [nReason, setNReason]       = useState("");
  const [nExpiry, setNExpiry]       = useState("");
  const [adding, setAdding]         = useState(false);

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
      await addUserOverride(selectedUser.id, { permission: nPerm, effect: nEffect, reason: nReason, expires_at: nExpiry || null });
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
      <div className="w-64 flex-shrink-0 border border-gray-200 rounded-xl overflow-hidden flex flex-col">
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
          <input className={INPUT} placeholder="Search users…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="overflow-y-auto flex-1">
          {filteredUsers.map((u) => (
            <button
              key={u.id}
              onClick={() => selectUser(u)}
              className={`w-full text-left px-3 py-2.5 border-b border-gray-100 transition-colors ${
                selectedUser?.id === u.id ? "bg-violet-50 text-violet-700" : "hover:bg-gray-50 text-gray-700"
              }`}
            >
              <p className="text-sm font-medium truncate">{u.full_name}</p>
              <p className="text-xs text-gray-400">{u.username}</p>
            </button>
          ))}
        </div>
      </div>

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

            {canManage && (
              <div className="p-4 border-b border-gray-200 bg-gray-50 space-y-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Add Override</p>
                <div className="flex gap-2 flex-wrap">
                  <Field label="Permission">
                    <select className={SELECT} value={nPerm} onChange={(e) => setNPerm(e.target.value)}>
                      <option value="">Select permission…</option>
                      {perms.map((p) => <option key={p.code} value={p.code}>{p.code}</option>)}
                    </select>
                  </Field>
                  <Field label="Effect">
                    <select className={SELECT} value={nEffect} onChange={(e) => setNEffect(e.target.value as "ALLOW" | "DENY")}>
                      <option value="ALLOW">ALLOW</option>
                      <option value="DENY">DENY</option>
                    </select>
                  </Field>
                  <Field label="Reason">
                    <input className={INPUT} placeholder="Optional reason" value={nReason} onChange={(e) => setNReason(e.target.value)} />
                  </Field>
                  <Field label="Expires (optional)">
                    <input type="datetime-local" className={INPUT} value={nExpiry} onChange={(e) => setNExpiry(e.target.value)} />
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
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${ov.effect === "ALLOW" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
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
                            <button onClick={() => removeOverride(ov.id)} className="text-red-500 hover:text-red-700 p-1 rounded">
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

  const showRoles     = can("settings.roles.manage");
  const showUserRoles = can("settings.users.manage") || can("settings.roles.manage");
  const showOverrides = can("settings.users.manage");

  const defaultTab: Tab = showRoles ? "roles" : showUserRoles ? "userroles" : "overrides";
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab);

  const tabs: { id: Tab; label: string; icon: React.ReactNode; visible: boolean }[] = [
    { id: "roles",     label: "Roles & Permissions",   icon: <ShieldCheck size={15} />, visible: showRoles },
    { id: "userroles", label: "User Roles",             icon: <Key size={15} />,         visible: showUserRoles },
    { id: "overrides", label: "Permission Overrides",   icon: <Users size={15} />,       visible: showOverrides },
  ];

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-violet-100 flex items-center justify-center">
          <ShieldCheck size={18} className="text-violet-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">Roles & Access</h1>
          <p className="text-xs text-gray-500">Manage roles, permissions and user access</p>
        </div>
      </div>

      <div className="flex border-b border-gray-200 gap-0.5 overflow-x-auto">
        {tabs.filter((t) => t.visible).map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px whitespace-nowrap ${
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

      <div className="flex-1 overflow-hidden">
        {activeTab === "roles"     && <RolesTab />}
        {activeTab === "userroles" && <UserRolesTab />}
        {activeTab === "overrides" && <OverridesTab />}
      </div>
    </div>
  );
}
