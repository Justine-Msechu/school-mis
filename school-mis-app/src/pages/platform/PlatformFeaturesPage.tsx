import { useEffect, useState } from "react";
import { RefreshCw, Layers, CheckCircle, XCircle } from "lucide-react";
import { getFeatureFlags, setFeatureFlag, type FeatureFlags } from "@/api/schools";

const PLANS = ["trial", "basic", "standard", "premium"] as const;

const MODULES: { key: string; label: string; description: string }[] = [
  { key: "grades",       label: "Grades & Results",     description: "Exam entry, report cards, GPA" },
  { key: "attendance",   label: "Attendance",            description: "Daily & period attendance" },
  { key: "finance",      label: "Finance",               description: "Fee collection, billing, payments" },
  { key: "enrollment",   label: "Enrollment",            description: "Student enrollment workflow" },
  { key: "guardians",    label: "Guardians",             description: "Parent & guardian records" },
  { key: "report_cards", label: "Report Cards",          description: "Printable report cards" },
  { key: "promotion",    label: "Promotion",             description: "Year-end student promotion" },
  { key: "reports",      label: "Reports & Analytics",   description: "Platform reports" },
  { key: "library",      label: "Library",               description: "Book catalog & loan tracking" },
  { key: "payroll",      label: "Payroll",               description: "Staff salary & payslips" },
  { key: "accounting",   label: "Accounting",            description: "Ledger, expenses, double-entry" },
  { key: "transport",    label: "Transport",             description: "Routes, vehicles, student assignment" },
  { key: "inventory",    label: "Inventory",             description: "Assets, stock, issue/receive" },
  { key: "health",       label: "Health",                description: "Clinic visits, health records" },
  { key: "welfare",      label: "Welfare",               description: "Student welfare & counselling" },
  { key: "ngo",          label: "NGO / Sponsorship",     description: "NGO partnerships & sponsorships" },
];

const PLAN_COLOR: Record<string, string> = {
  trial:    "#0891B2",
  basic:    "#2563EB",
  standard: "#7C3AED",
  premium:  "#059669",
};

export default function PlatformFeaturesPage() {
  const [flags,   setFlags]   = useState<FeatureFlags>({});
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);
  const [error,   setError]   = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await getFeatureFlags();
      setFlags(res.data);
    } catch {
      setError("Failed to load feature flags.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (plan: string, module: string) => {
    const key = `${plan}:${module}`;
    const current = flags[plan]?.[module] ?? false;
    setToggling(key);
    try {
      await setFeatureFlag(plan, module, !current);
      setFlags(f => ({
        ...f,
        [plan]: { ...(f[plan] ?? {}), [module]: !current },
      }));
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Module Access Control</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Define which modules are available for each subscription plan
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <div className="w-7 h-7 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 text-sm text-red-700">{error}</div>
      )}

      {!loading && !error && (
        <>
          {/* Plan summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            {PLANS.map(plan => {
              const enabled = Object.values(flags[plan] ?? {}).filter(Boolean).length;
              return (
                <div key={plan} className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers size={14} style={{ color: PLAN_COLOR[plan] }} />
                    <span className="text-xs font-semibold capitalize" style={{ color: PLAN_COLOR[plan] }}>
                      {plan}
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{enabled}</p>
                  <p className="text-xs text-gray-400 mt-0.5">of {MODULES.length} modules</p>
                </div>
              );
            })}
          </div>

          {/* Feature matrix */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide w-[45%]">
                    Module
                  </th>
                  {PLANS.map(plan => (
                    <th key={plan} className="px-4 py-3.5 text-center text-xs font-semibold uppercase tracking-wide"
                      style={{ color: PLAN_COLOR[plan] }}>
                      {plan}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MODULES.map((mod, i) => (
                  <tr key={mod.key} className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${i % 2 === 0 ? "" : "bg-gray-50/30"}`}>
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900 text-sm">{mod.label}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{mod.description}</p>
                    </td>
                    {PLANS.map(plan => {
                      const enabled = flags[plan]?.[mod.key] ?? false;
                      const key = `${plan}:${mod.key}`;
                      const busy = toggling === key;
                      return (
                        <td key={plan} className="px-4 py-3 text-center">
                          <button
                            onClick={() => toggle(plan, mod.key)}
                            disabled={busy}
                            title={enabled ? `Disable for ${plan}` : `Enable for ${plan}`}
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all ${
                              busy ? "opacity-40" : "hover:scale-110"
                            } ${
                              enabled
                                ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
                                : "bg-gray-100 text-gray-300 hover:bg-gray-200 hover:text-gray-400"
                            }`}
                          >
                            {enabled
                              ? <CheckCircle size={16} />
                              : <XCircle size={16} />
                            }
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-gray-400 mt-3">
            Changes take effect immediately for new logins. Feature access enforcement requires schools to be on the
            matching plan.
          </p>
        </>
      )}
    </div>
  );
}
