import { useState, useEffect } from "react";
import { Users, Plus, Edit2, ToggleLeft, ToggleRight } from "lucide-react";
import { getUsers, getRoles, createUser, updateUser, toggleUserActive, type AppUser, type Role } from "@/api/settings";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

function RoleBadge({ role, label, color }: { role: string; label: string; color: string }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ background: color + "22", color }}>
      {label}
    </span>
  );
}

interface UserFormProps {
  roles: Role[];
  initial?: AppUser;
  onSave: (data: { full_name: string; role: string; password?: string } & { username?: string }) => void;
  onCancel: () => void;
}

function UserForm({ roles, initial, onSave, onCancel }: UserFormProps) {
  const [username, setUsername]   = useState(initial?.username || "");
  const [fullName, setFullName]   = useState(initial?.full_name || "");
  const [role, setRole]           = useState(initial?.role || roles[0]?.key || "");
  const [password, setPassword]   = useState("");
  const [saving, setSaving]       = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      const payload: any = { full_name: fullName, role };
      if (!initial) payload.username = username;
      if (password) payload.password = password;
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit User" : "New User"}</h2>
        <div className="flex flex-col gap-3">
          {!initial && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Username</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)}
                className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Full Name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)}
              className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
              {roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Password {initial && <span className="text-gray-400">(leave blank to keep current)</span>}
            </label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [users, setUsers]       = useState<AppUser[]>([]);
  const [roles, setRoles]       = useState<Role[]>([]);
  const [loading, setLoading]   = useState(true);
  const [editUser, setEditUser] = useState<AppUser | null | "new">(null);

  const load = () => {
    setLoading(true);
    Promise.all([getUsers(), getRoles()])
      .then(([u, r]) => { setUsers(u); setRoles(r); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (data: any) => {
    try {
      if (editUser === "new") {
        await createUser(data);
      } else if (editUser) {
        await updateUser(editUser.id, data);
      }
      setEditUser(null);
      load();
    } catch {
      // ignore
    }
  };

  const handleToggle = async (id: number) => {
    await toggleUserActive(id).catch(() => {});
    load();
  };

  const roleMap = Object.fromEntries(roles.map((r) => [r.key, r]));

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500 mt-0.5">User accounts and system configuration</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setEditUser("new")}>Add User</Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Username</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : users.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="py-16">
                    <EmptyState icon={Users} title="No users found" />
                  </td>
                </tr>
              )
              : users.map((u) => {
                const role = roleMap[u.role];
                return (
                  <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                    <td className="px-4 py-3 text-gray-500">@{u.username}</td>
                    <td className="px-4 py-3">
                      {role
                        ? <RoleBadge role={u.role} label={role.label} color={role.color} />
                        : <span className="text-gray-400 text-xs">{u.role}</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      {u.is_active
                        ? <Badge variant="green">Active</Badge>
                        : <Badge variant="red">Inactive</Badge>
                      }
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setEditUser(u)}
                          className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => handleToggle(u.id)}
                          className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors"
                        >
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

      {editUser !== null && (
        <UserForm
          roles={roles}
          initial={editUser === "new" ? undefined : editUser}
          onSave={handleSave}
          onCancel={() => setEditUser(null)}
        />
      )}
    </div>
  );
}
