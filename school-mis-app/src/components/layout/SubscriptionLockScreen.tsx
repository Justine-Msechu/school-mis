import { useState } from "react";
import { Lock, RefreshCw, CheckCircle } from "lucide-react";
import { activateSubscription } from "@/api/subscription";
import { useAuthStore } from "@/stores/authStore";

const PLANS = [
  { key: "standard", label: "Standard",  desc: "Up to 150 users",     color: "#0891B2" },
  { key: "premium",  label: "Premium",   desc: "Up to 500 users",     color: "#7C3AED" },
  { key: "lifetime", label: "Lifetime",  desc: "Unlimited — one-off", color: "#059669" },
  { key: "trial",    label: "Extend Trial", desc: "30 more days",     color: "#F59E0B" },
];

export default function SubscriptionLockScreen({ onUnlocked }: { onUnlocked: () => void }) {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [plan, setPlan]         = useState("standard");
  const [trialDays, setTrialDays] = useState("30");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");
  const [done, setDone]         = useState(false);

  const activate = async () => {
    setSaving(true);
    setError("");
    try {
      let trialEnds: string | undefined;
      if (plan === "trial") {
        const d = new Date();
        d.setDate(d.getDate() + parseInt(trialDays || "30"));
        trialEnds = d.toISOString().split("T")[0];
      }
      await activateSubscription(plan, undefined, trialEnds);
      setDone(true);
      setTimeout(onUnlocked, 1500);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Activation failed. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/90">
        <div className="text-center text-white">
          <CheckCircle size={56} className="mx-auto mb-4 text-green-400" />
          <p className="text-xl font-bold">Subscription activated!</p>
          <p className="text-gray-400 mt-1">Resuming…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/95 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-red-600 px-6 py-5 text-white text-center">
          <Lock size={32} className="mx-auto mb-2" />
          <h2 className="text-xl font-bold">Subscription Expired</h2>
          <p className="text-red-200 text-sm mt-1">
            {isAdmin
              ? "Reactivate below to restore access for all staff."
              : "Contact your administrator to reactivate the system."}
          </p>
        </div>

        <div className="p-6">
          {!isAdmin ? (
            <div className="text-center py-4">
              <p className="text-gray-600 text-sm leading-relaxed">
                The system has been locked because the subscription has expired.
                Only the <strong>Administrator</strong> can reactivate it.
              </p>
              <p className="mt-4 text-xs text-gray-400">
                Ask your administrator to log in and activate a plan.
              </p>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                  {error}
                </div>
              )}

              <p className="text-sm text-gray-600 mb-4">Select a plan to reactivate:</p>

              <div className="grid grid-cols-2 gap-2 mb-4">
                {PLANS.map((p) => (
                  <button
                    key={p.key}
                    onClick={() => setPlan(p.key)}
                    className={`p-3 rounded-xl border-2 text-left transition-all ${
                      plan === p.key
                        ? "border-violet-500 bg-violet-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-semibold text-sm text-gray-900">{p.label}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{p.desc}</div>
                  </button>
                ))}
              </div>

              {plan === "trial" && (
                <div className="mb-4">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Extension days
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={trialDays}
                    onChange={(e) => setTrialDays(e.target.value)}
                    className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>
              )}

              <button
                onClick={activate}
                disabled={saving}
                className="w-full h-11 bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors"
              >
                {saving ? (
                  <><RefreshCw size={16} className="animate-spin" /> Activating…</>
                ) : (
                  "Activate & Unlock System"
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
