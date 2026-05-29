import { useState, useEffect } from "react";
import { ShieldCheck, Plus, Trash2, Search, Building2, RefreshCw } from "lucide-react";
import { getSuperAdminUsers, type PlatformUser } from "@/api/schools";
import { getRbacRoles, getUserRoles, setUserRoles, type RbacRole } from "@/api/rbac";
import Button from "@/components/ui/Button";
import SkeletonRow from "@/components/ui/SkeletonRow";

const SELECT =
  "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500";

const ROLE_COLORS: Record<string, string> = {
  admin:           "#7C3AED",
  head_teacher:    "#0891B2",
  class_teacher:   "#059669",
  subject_teacher: "#D97706",
  superadmin:      "#DC2626",
};

function roleBadgeStyle(role: string) {
  const color = ROLE_COLORS[role] ?? "#6B7280";
  return { backgroundColor: `${color}18`, color };
}

export default function PlatformRbacPage() {
  const [users, setUsers]           = useState<PlatformUser[]>([]);
  const [allRoles, setAllRoles]     = useState<RbacRole[]>([]);
  const [selectedUser, setSelectedUser] = useState<PlatformUser | null>(null);
  const [userRoles, setUserRoles_]  = useState<{ id: number; name: string; label: string; color: string }[]>([]);
  const [schoolFilter, setSchoolFilter] = useState("all");
  const [search, setSearch]         = useState("");
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [error, setError]           = useState("");
  const [addRoleId, setAddRoleId]   = useState<number | "">("");
  const [saving, setSaving]         = useState(false);

  const load = async () => {
    setLoadingUsers(true);
    setError("");
    try {
      const [u, r] = await Promise.all([getSuperAdminUsers(), getRbacRoles()]);
      setUsers(u);
      setAllRoles(r);
    } catch {
      setError("Failed to load users or roles.");
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => { load(); }, []);

  async function selectUser(u: PlatformUser) {
    setSelectedUser(u);
    setAddRoleId("");
    setLoadingRoles(true);
    setError("");
    try {
      const data = await getUserRoles(u.id);
      setUserRoles_(data.roles);
    } catch {
      setError("Failed to load user roles.");
    } finally {
      setLoadingRoles(false);
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
      setError(e?.response?.data?.detail ?? "Failed to add role.");
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
      setError("Failed to remove role.");
    } finally {
      setSaving(false);
    }
  }

  // Unique schools for the filter dropdown
  const schools = Array.from(
    new Map(
      users
        .filter((u) => u.school_id !== null)
        .map((u) => [u.school_id, { id: u.school_id!, name: u.school_name ?? "Unknown" }])
    ).values()
  ).sort((a, b) => a.name.localeCompare(b.name));

  const filteredUsers = users.filter((u) => {
    const matchSchool = schoolFilter === "all" || String(u.school_id) === schoolFilter;
    const q = search.toLowerCase();
    const matchSearch = !q ||
      u.full_name.toLowerCase().includes(q) ||
      u.username.toLowerCase().includes(q) ||
      (u.school_name ?? "").toLowerCase().includes(q);
    return matchSchool && matchSearch;
  });

  const assignedIds    = new Set(userRoles.map((r) => r.id));
  const availableRoles = allRoles.filter((r) => !assignedIds.has(r.id));

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-red-100 flex items-center justify-center">
            <ShieldCheck size={18} className="text-red-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Roles &amp; Access</h1>
            <p className="text-xs text-gray-500">Grant or revoke roles across all registered schools</p>
          </div>
        </div>
        <button
          onClick={load}
          disabled={loadingUsers}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loadingUsers ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Main two-panel layout */}
      <div className="flex gap-4 flex-1 overflow-hidden min-h-0">

        {/* Left: user list */}
        <div className="w-72 flex-shrink-0 border border-gray-200 rounded-xl overflow-hidden flex flex-col bg-white">
          <div className="p-2.5 bg-gray-50 border-b border-gray-200 space-y-2">
            {/* School filter */}
            <div className="relative">
              <Building2 size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <select
                value={schoolFilter}
                onChange={(e) => setSchoolFilter(e.target.value)}
                className="w-full h-8 pl-8 pr-3 border border-gray-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="all">All schools ({users.length} users)</option>
                {schools.map((s) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            {/* Search */}
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="w-full h-8 pl-8 pr-3 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="Search by name or username…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="overflow-y-auto flex-1">
            {loadingUsers ? (
              <div className="p-3"><SkeletonRow /></div>
            ) : filteredUsers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400 gap-2">
                <Building2 size={28} className="opacity-40" />
                <p className="text-xs">No users match your filters</p>
              </div>
            ) : (
              filteredUsers.map((u) => (
                <button
                  key={u.id}
                  onClick={() => selectUser(u)}
                  className={`w-full text-left px-3 py-2.5 border-b border-gray-100 transition-colors ${
                    selectedUser?.id === u.id
                      ? "bg-violet-50 text-violet-700"
                      : "hover:bg-gray-50 text-gray-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{u.full_name}</p>
                      <p className="text-xs text-gray-400 truncate">{u.username}</p>
                      {u.school_name && (
                        <p className="text-xs text-gray-400 truncate mt-0.5">{u.school_name}</p>
                      )}
                    </div>
                    <span
                      className="flex-shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold capitalize"
                      style={roleBadgeStyle(u.role)}
                    >
                      {u.role.replace("_", " ")}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="px-3 py-2 bg-gray-50 border-t border-gray-200">
            <p className="text-xs text-gray-400">
              {filteredUsers.length} user{filteredUsers.length !== 1 ? "s" : ""}
              {schoolFilter !== "all" || search ? " (filtered)" : ""}
            </p>
          </div>
        </div>

        {/* Right: role management */}
        <div className="flex-1 border border-gray-200 rounded-xl overflow-hidden flex flex-col bg-white">
          {!selectedUser ? (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
              <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center">
                <ShieldCheck size={24} className="opacity-40" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-gray-500">Select a user</p>
                <p className="text-xs text-gray-400 mt-0.5">Choose a user from the list to manage their roles</p>
              </div>
            </div>
          ) : (
            <>
              {/* Selected user header */}
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-xl bg-violet-100 flex items-center justify-center flex-shrink-0 text-sm font-bold text-violet-700">
                      {selectedUser.full_name.split(" ").slice(0, 2).map((n) => n[0]).join("").toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-gray-800">{selectedUser.full_name}</span>
                        <span className="text-xs text-gray-400">{selectedUser.username}</span>
                        <span
                          className="px-1.5 py-0.5 rounded text-[10px] font-semibold capitalize"
                          style={roleBadgeStyle(selectedUser.role)}
                        >
                          {selectedUser.role.replace("_", " ")}
                        </span>
                      </div>
                      {selectedUser.school_name && (
                        <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                          <Building2 size={11} /> {selectedUser.school_name}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 flex-shrink-0">
                    {userRoles.length} role{userRoles.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>

              {/* Role list */}
              {loadingRoles ? (
                <div className="p-4"><SkeletonRow /></div>
              ) : (
                <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
                  {userRoles.length === 0 ? (
                    <div className="flex items-center justify-center py-12 text-gray-400 text-sm">
                      No roles assigned to this user
                    </div>
                  ) : (
                    userRoles.map((role) => (
                      <div key={role.id} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors">
                        <div className="flex items-center gap-3">
                          <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: role.color }} />
                          <div>
                            <p className="text-sm font-medium text-gray-800">{role.label}</p>
                            <p className="text-xs font-mono text-gray-400">{role.name}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeRole(role.id)}
                          disabled={saving}
                          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 transition-colors disabled:opacity-40"
                        >
                          <Trash2 size={13} /> Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Add role footer */}
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-end gap-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Add role</label>
                  <select
                    className={SELECT}
                    value={addRoleId}
                    onChange={(e) => setAddRoleId(+e.target.value || "")}
                    disabled={availableRoles.length === 0 || loadingRoles}
                  >
                    <option value="">
                      {availableRoles.length === 0 ? "All roles already assigned" : "Select role to add…"}
                    </option>
                    {availableRoles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
                <Button size="sm" onClick={addRole} disabled={!addRoleId || saving || loadingRoles}>
                  <Plus size={13} className="mr-1" />
                  {saving ? "Saving…" : "Add"}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
