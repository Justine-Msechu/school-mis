import { useState } from "react";
import { KeyRound } from "lucide-react";
import { changePassword } from "@/api/auth";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { useToast } from "@/components/ui/Toast";

export default function ForceChangePassword() {
  const { mustChangePw, setMustChangePw } = useAuthStore();
  const toast = useToast();
  const [current, setCurrent]   = useState("");
  const [next, setNext]         = useState("");
  const [confirm, setConfirm]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  if (!mustChangePw) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (next.length < 8) { setError("New password must be at least 8 characters"); return; }
    if (next !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true);
    try {
      await changePassword(current, next);
      setMustChangePw(false);
      toast.success("Password changed successfully");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center mb-3">
            <KeyRound size={22} className="text-amber-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Change Your Password</h2>
          <p className="text-sm text-gray-500 text-center mt-1">
            Your account requires a password change before you can continue.
          </p>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Current Password</label>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              autoFocus
              className="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter current password"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">New Password</label>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              className="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Confirm New Password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              className="w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Repeat new password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="mt-2 h-10 w-full bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Saving…" : "Set New Password"}
          </button>

          <button
            type="button"
            onClick={async () => {
              try { await api.post("/auth/dismiss-force-change"); } catch { /* ignore */ }
              setMustChangePw(false);
            }}
            className="h-8 w-full text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Skip for now
          </button>
        </form>
      </div>
    </div>
  );
}
