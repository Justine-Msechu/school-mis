import { useState } from "react";
import { Check, Zap, Shield, Star, Crown, Loader2 } from "lucide-react";
import api from "@/api/client";
import { useSubscriptionStore } from "@/stores/subscriptionStore";
import { useAuthStore } from "@/stores/authStore";

const PLANS = [
  {
    key: "trial",
    label: "Free Trial",
    price: "Free",
    duration: "30 days",
    icon: Zap,
    color: "blue",
    description: "Try everything with no commitment. No credit card required.",
    features: [
      "All core modules included",
      "Up to 50 students",
      "Attendance & Grades",
      "Finance & Fees",
      "Reports & Report Cards",
    ],
  },
  {
    key: "basic",
    label: "Basic",
    price: "TZS 50,000",
    duration: "/ month",
    icon: Shield,
    color: "green",
    description: "Essential tools for small schools.",
    features: [
      "Everything in Trial",
      "Library management",
      "Payroll module",
      "Up to 200 students",
      "Email support",
    ],
  },
  {
    key: "standard",
    label: "Standard",
    price: "TZS 100,000",
    duration: "/ month",
    icon: Star,
    color: "violet",
    description: "Complete solution for growing schools.",
    features: [
      "Everything in Basic",
      "Transport & Inventory",
      "Accounting module",
      "Up to 500 students",
      "Priority support",
    ],
  },
  {
    key: "premium",
    label: "Premium",
    price: "TZS 200,000",
    duration: "/ month",
    icon: Crown,
    color: "amber",
    description: "Full platform access for large institutions.",
    features: [
      "All modules unlocked",
      "Unlimited students",
      "NGO & Welfare tools",
      "Health & AI features",
      "Dedicated support",
    ],
  },
];

const COLOR_MAP: Record<string, { card: string; badge: string; btn: string; icon: string }> = {
  blue:   { card: "border-blue-200 bg-blue-50/40",   badge: "bg-blue-100 text-blue-700",   btn: "bg-blue-600 hover:bg-blue-700",   icon: "bg-blue-100 text-blue-600"   },
  green:  { card: "border-green-200 bg-green-50/40",  badge: "bg-green-100 text-green-700",  btn: "bg-green-600 hover:bg-green-700",  icon: "bg-green-100 text-green-600"  },
  violet: { card: "border-violet-200 bg-violet-50/40",badge: "bg-violet-100 text-violet-700",btn: "bg-violet-600 hover:bg-violet-700",icon: "bg-violet-100 text-violet-600" },
  amber:  { card: "border-amber-200 bg-amber-50/40",  badge: "bg-amber-100 text-amber-700",  btn: "bg-amber-600 hover:bg-amber-700",  icon: "bg-amber-100 text-amber-600"  },
};

export default function PlanSelectionModal() {
  const { user } = useAuthStore();
  const fetchSub = useSubscriptionStore((s) => s.fetch);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ status: string; message: string } | null>(null);
  const [error, setError] = useState("");

  const handleSelect = async (planKey: string) => {
    setSelected(planKey);
    setError("");
    setLoading(true);
    try {
      const res = await api.post<{ status: string; message: string; trial_ends?: string }>(
        "/subscriptions/select-initial-plan",
        { plan_name: planKey },
      );
      setResult(res.data);
      // Refresh subscription state so the modal disappears
      await fetchSub();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Something went wrong. Please try again.");
      setSelected(null);
    } finally {
      setLoading(false);
    }
  };

  // Paid plan selected — show bank transfer instructions
  if (result && result.status === "pending") {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 text-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-100 flex items-center justify-center mx-auto mb-4">
            <Shield size={28} className="text-amber-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Request Submitted</h2>
          <p className="text-sm text-gray-500 mb-6">{result.message}</p>
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 text-left mb-6">
            <p className="text-xs font-semibold text-gray-600 mb-2">Bank Transfer Details</p>
            <div className="space-y-1 text-sm text-gray-700">
              <p><span className="font-medium">Bank:</span> CRDB Bank</p>
              <p><span className="font-medium">Account:</span> 01J1234567890</p>
              <p><span className="font-medium">Account Name:</span> YouthTech Solutions Ltd</p>
              <p><span className="font-medium">Reference:</span> {user?.full_name ?? "Your School Name"}</p>
            </div>
          </div>
          <p className="text-xs text-gray-400">
            Once payment is received the platform admin will activate your account within 24 hours.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl my-6">
        {/* Header */}
        <div className="px-8 pt-8 pb-6 text-center border-b border-gray-100">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Choose Your Plan</h1>
          <p className="text-sm text-gray-500">
            Select a plan to get started. You can upgrade anytime.
          </p>
        </div>

        {/* Plan cards */}
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {PLANS.map((plan) => {
            const c = COLOR_MAP[plan.color];
            const Icon = plan.icon;
            const isLoading = loading && selected === plan.key;

            return (
              <div
                key={plan.key}
                className={`relative rounded-2xl border-2 p-5 flex flex-col transition-shadow ${c.card} ${
                  plan.key === "trial" ? "ring-2 ring-blue-400 ring-offset-1" : ""
                }`}
              >
                {plan.key === "trial" && (
                  <span className={`absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-semibold px-3 py-0.5 rounded-full ${c.badge}`}>
                    Recommended
                  </span>
                )}

                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${c.icon}`}>
                  <Icon size={20} />
                </div>

                <p className="text-base font-bold text-gray-900">{plan.label}</p>
                <p className="text-xs text-gray-500 mb-3">{plan.description}</p>

                <div className="mb-4">
                  <span className="text-xl font-extrabold text-gray-900">{plan.price}</span>
                  <span className="text-xs text-gray-500 ml-1">{plan.duration}</span>
                </div>

                <ul className="space-y-1.5 flex-1 mb-5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-gray-600">
                      <Check size={13} className="text-green-500 flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelect(plan.key)}
                  disabled={loading}
                  className={`w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-2 ${c.btn}`}
                >
                  {isLoading ? <Loader2 size={15} className="animate-spin" /> : null}
                  {plan.key === "trial" ? "Start Free Trial" : `Choose ${plan.label}`}
                </button>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mx-6 mb-6 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 text-center">
            {error}
          </div>
        )}

        <p className="text-center text-xs text-gray-400 pb-6">
          Paid plans use bank transfer. Your account will be activated within 24 hours of payment.
        </p>
      </div>
    </div>
  );
}
