import { useState } from "react";
import { Save, KeyRound, User } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { changePassword } from "@/api/auth";

const INPUT = "w-full h-9 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ChangePasswordPanel() {
  const [current, setCurrent] = useState("");
  const [next,    setNext]    = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving,  setSaving]  = useState(false);
  const [msg,     setMsg]     = useState<{ ok: boolean; text: string } | null>(null);

  const submit = async () => {
    setMsg(null);
    if (next.length < 8) { setMsg({ ok: false, text: "New password must be at least 8 characters." }); return; }
    if (next !== confirm) { setMsg({ ok: false, text: "Passwords do not match." }); return; }
    setSaving(true);
    try {
      await changePassword(current, next);
      setMsg({ ok: true, text: "Password updated successfully." });
      setCurrent(""); setNext(""); setConfirm("");
    } catch (e: any) {
      setMsg({ ok: false, text: e?.response?.data?.detail ?? "Failed to update password." });
    } finally { setSaving(false); }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 max-w-md">
      <div className="flex items-center gap-2 mb-4">
        <KeyRound size={16} className="text-gray-400" />
        <h2 className="text-sm font-semibold text-gray-900">Change Password</h2>
      </div>

      {msg && (
        <div className={`mb-4 px-3 py-2.5 rounded-lg text-xs border ${
          msg.ok
            ? "bg-green-50 border-green-200 text-green-700"
            : "bg-red-50 border-red-200 text-red-700"
        }`}>
          {msg.text}
        </div>
      )}

      <div className="space-y-3">
        <Field label="Current password">
          <input type="password" className={INPUT} value={current} onChange={e => setCurrent(e.target.value)} />
        </Field>
        <Field label="New password">
          <input type="password" className={INPUT} value={next} onChange={e => setNext(e.target.value)} />
        </Field>
        <Field label="Confirm new password">
          <input type="password" className={INPUT} value={confirm} onChange={e => setConfirm(e.target.value)} />
        </Field>
      </div>

      <button
        onClick={submit}
        disabled={saving || !current || !next || !confirm}
        className="mt-4 flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-xl transition-colors"
      >
        <Save size={14} />
        {saving ? "Saving…" : "Update Password"}
      </button>
    </div>
  );
}

export default function PlatformSettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Platform Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage your platform admin account</p>
      </div>

      {/* Account info (read-only) */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 max-w-md">
        <div className="flex items-center gap-2 mb-4">
          <User size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-900">Account Info</h2>
        </div>
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-gray-500">Full name</p>
            <p className="text-sm text-gray-900 mt-0.5">{user?.full_name ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Username</p>
            <p className="text-sm text-gray-900 mt-0.5 font-mono">@{user?.username ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Role</p>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-50 text-red-700 mt-0.5">
              Platform Admin
            </span>
          </div>
        </div>
      </div>

      <ChangePasswordPanel />
    </div>
  );
}
