import { Lock, ArrowRight, X } from "lucide-react";

const PLAN_ORDER = ["basic", "standard", "premium"];

const PLAN_INFO: Record<string, { label: string; color: string; features: string[] }> = {
  basic:    { label: "Basic",    color: "#0891B2", features: ["Students & Classes", "Attendance", "Grades & Reports", "Basic Finance"] },
  standard: { label: "Standard", color: "#7C3AED", features: ["Everything in Basic", "Payroll", "Transport", "Inventory", "Library", "Welfare", "NGO Partners"] },
  premium:  { label: "Premium",  color: "#059669", features: ["Everything in Standard", "AI Chat Assistant", "Multi-school network", "API access"] },
};

interface Props {
  currentPlan: string;
  requiredPlan: string;
  message: string;
  onDismiss: () => void;
}

export default function PlanUpgradeOverlay({ currentPlan, requiredPlan, message, onDismiss }: Props) {
  const required = PLAN_INFO[requiredPlan] ?? PLAN_INFO.standard;
  const current  = PLAN_INFO[currentPlan]  ?? { label: currentPlan, color: "#94A3B8", features: [] };

  const upgradePlans = PLAN_ORDER.slice(PLAN_ORDER.indexOf(requiredPlan)).map(k => PLAN_INFO[k]).filter(Boolean);

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center bg-white/80 backdrop-blur-sm">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-amber-50 border border-amber-100">
              <Lock size={18} className="text-amber-600" />
            </div>
            <div>
              <p className="font-bold text-gray-900">Feature Locked</p>
              <p className="text-xs text-gray-500">Not available on your current plan</p>
            </div>
          </div>
          <button onClick={onDismiss} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
            <X size={16} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-gray-600">{message}</p>

          {/* Current → Required */}
          <div className="flex items-center gap-3">
            <div className="flex-1 rounded-xl border border-gray-200 px-3 py-2 text-center">
              <p className="text-xs text-gray-400 mb-0.5">Current plan</p>
              <p className="font-bold text-sm" style={{ color: current.color }}>{current.label}</p>
            </div>
            <ArrowRight size={16} className="text-gray-400 flex-shrink-0" />
            <div className="flex-1 rounded-xl border-2 px-3 py-2 text-center" style={{ borderColor: required.color, backgroundColor: `${required.color}10` }}>
              <p className="text-xs text-gray-400 mb-0.5">Required plan</p>
              <p className="font-bold text-sm" style={{ color: required.color }}>{required.label} or higher</p>
            </div>
          </div>

          {/* What you get */}
          <div className="space-y-1.5">
            {upgradePlans[0]?.features.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: required.color }} />
                {f}
              </div>
            ))}
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
            Contact your administrator to upgrade the subscription plan.
          </div>
        </div>
      </div>
    </div>
  );
}
