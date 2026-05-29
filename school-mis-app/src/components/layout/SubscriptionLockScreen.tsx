import { useState } from "react";
import { Lock, PhoneCall, Check, Shield, Star, Crown, Loader2 } from "lucide-react";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { useSubscriptionStore } from "@/stores/subscriptionStore";

const UPGRADE_PLANS = [
  {
    key: "basic",
    label: "Basic",
    price: "TZS 50,000",
    icon: Shield,
    color: "green",
    features: ["All core modules", "Up to 200 students", "Library & Payroll", "Email support"],
  },
  {
    key: "standard",
    label: "Standard",
    price: "TZS 100,000",
    icon: Star,
    color: "violet",
    features: ["Everything in Basic", "Transport & Inventory", "Accounting", "Up to 500 students"],
  },
  {
    key: "premium",
    label: "Premium",
    price: "TZS 200,000",
    icon: Crown,
    color: "amber",
    features: ["All modules", "Unlimited students", "AI features", "Dedicated support"],
  },
];

const COLORS: Record<string, { card: string; btn: string; icon: string }> = {
  green:  { card: "border-green-200 bg-green-50/40",   btn: "bg-green-600 hover:bg-green-700",   icon: "bg-green-100 text-green-600"   },
  violet: { card: "border-violet-200 bg-violet-50/40", btn: "bg-violet-600 hover:bg-violet-700", icon: "bg-violet-100 text-violet-600" },
  amber:  { card: "border-amber-200 bg-amber-50/40",   btn: "bg-amber-600 hover:bg-amber-700",   icon: "bg-amber-100 text-amber-600"   },
};

export default function SubscriptionLockScreen() {
  const { user }  = useAuthStore();
  const plan      = useSubscriptionStore((s) => s.plan);
  const daysLeft  = useSubscriptionStore((s) => s.daysLeft);

  const role = user?.role ?? "staff";
  const isAdmin = role === "admin";

  const [loading, setLoading] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState("");

  const handleUpgradeRequest = async (planKey: string) => {
    setLoading(planKey);
    setError("");
    try {
      await api.post("/subscriptions/request-upgrade", { plan_name: planKey, interval: "monthly" });
      setSubmitted(planKey);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Something went wrong. Please try again.");
    } finally {
      setLoading(null);
    }
  };

  if (submitted) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/95 p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden text-center p-8">
          <div className="w-14 h-14 rounded-full bg-green-50 border border-green-100 flex items-center justify-center mx-auto mb-4">
            <Check size={28} className="text-green-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Request Submitted</h2>
          <p className="text-sm text-gray-500 mb-4">
            Your request for the <span className="font-semibold capitalize">{submitted}</span> plan has been sent to the platform administrator.
          </p>
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 text-left text-sm text-gray-700 mb-4">
            <p className="font-semibold text-gray-600 mb-2">Bank Transfer Details</p>
            <p><span className="font-medium">Bank:</span> CRDB Bank</p>
            <p><span className="font-medium">Account:</span> 01J1234567890</p>
            <p><span className="font-medium">Account Name:</span> YouthTech Solutions Ltd</p>
            <p><span className="font-medium">Reference:</span> {user?.full_name ?? "Your School Name"}</p>
          </div>
          <p className="text-xs text-gray-400">Your account will be activated within 24 hours of payment.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/95 p-4 overflow-y-auto">
      <div className="w-full max-w-3xl my-6 bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-red-600 px-6 py-6 text-white text-center">
          <Lock size={36} className="mx-auto mb-3" />
          <h2 className="text-xl font-bold">Subscription Expired</h2>
          <p className="text-red-200 text-sm mt-1">
            Access has been suspended until the subscription is renewed.
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="rounded-xl bg-gray-50 border border-gray-200 px-4 py-3 text-sm text-gray-700">
            <p>Current plan: <span className="font-semibold capitalize">{plan}</span></p>
            {daysLeft !== null && (
              <p className="mt-0.5 text-red-600 font-medium">
                {daysLeft === 0 ? "Expired today" : `Expired ${Math.abs(daysLeft)} day(s) ago`}
              </p>
            )}
          </div>

          {!isAdmin && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-4 text-sm text-amber-900">
              <div className="flex items-start gap-2">
                <PhoneCall size={16} className="mt-0.5 flex-shrink-0 text-amber-600" />
                <p>Contact the platform administrator to renew and restore access.</p>
              </div>
            </div>
          )}

          {isAdmin && (
            <>
              <p className="text-sm font-semibold text-gray-700 text-center pt-2">
                Choose a plan to restore access
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {UPGRADE_PLANS.map((p) => {
                  const c = COLORS[p.color];
                  const Icon = p.icon;
                  const isLoading = loading === p.key;
                  return (
                    <div key={p.key} className={`rounded-2xl border-2 p-4 flex flex-col ${c.card}`}>
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-2 ${c.icon}`}>
                        <Icon size={18} />
                      </div>
                      <p className="text-sm font-bold text-gray-900">{p.label}</p>
                      <p className="text-base font-extrabold text-gray-900 mb-3">{p.price}<span className="text-xs text-gray-500 font-normal ml-1">/mo</span></p>
                      <ul className="space-y-1 flex-1 mb-4">
                        {p.features.map((f) => (
                          <li key={f} className="flex items-start gap-1.5 text-xs text-gray-600">
                            <Check size={11} className="text-green-500 flex-shrink-0 mt-0.5" />
                            {f}
                          </li>
                        ))}
                      </ul>
                      <button
                        onClick={() => handleUpgradeRequest(p.key)}
                        disabled={loading !== null}
                        className={`w-full py-2 rounded-xl text-xs font-semibold text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5 ${c.btn}`}
                      >
                        {isLoading && <Loader2 size={13} className="animate-spin" />}
                        Request Upgrade
                      </button>
                    </div>
                  );
                })}
              </div>
              {error && (
                <p className="text-center text-sm text-red-600">{error}</p>
              )}
              <p className="text-center text-xs text-gray-400">
                Paid plans use bank transfer. Your account will be activated within 24 hours of payment.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
