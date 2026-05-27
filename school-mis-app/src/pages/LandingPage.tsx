import { useNavigate } from "react-router-dom";
import {
  BookOpen, Users, GraduationCap, DollarSign, Bus, Package,
  Heart, BarChart2, Check, ArrowRight, Shield,
} from "lucide-react";

const FEATURES = [
  { icon: Users,         label: "Student & Staff Management" },
  { icon: GraduationCap, label: "Grades & Report Cards" },
  { icon: DollarSign,    label: "Finance & Accounting" },
  { icon: Bus,           label: "Transport Management" },
  { icon: Package,       label: "Inventory & Library" },
  { icon: Heart,         label: "Health & Welfare" },
  { icon: BarChart2,     label: "Reports & Analytics" },
  { icon: Shield,        label: "Role-based Access Control" },
];

const PLANS = [
  {
    key:   "basic",
    label: "Basic",
    color: "#0891B2",
    price: "Free trial",
    features: [
      "Students & Classes",
      "Attendance tracking",
      "Grades & Report cards",
      "Basic Finance",
      "Health records",
      "Up to 5 staff accounts",
    ],
  },
  {
    key:      "standard",
    label:    "Standard",
    color:    "#7C3AED",
    price:    "Contact us",
    popular:  true,
    features: [
      "Everything in Basic",
      "Payroll management",
      "Transport management",
      "Inventory control",
      "Library system",
      "Welfare & NGO Partners",
    ],
  },
  {
    key:   "premium",
    label: "Premium",
    color: "#059669",
    price: "Contact us",
    features: [
      "Everything in Standard",
      "AI Chat Assistant",
      "Advanced analytics",
      "API access",
      "Priority support",
      "Unlimited staff accounts",
    ],
  },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-100 max-w-6xl mx-auto">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <BookOpen size={16} className="text-white" />
          </div>
          <span className="font-bold text-gray-900 text-lg">School MIS</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-violet-600 transition-colors"
          >
            Sign in
          </button>
          <button
            onClick={() => navigate("/register")}
            className="px-4 py-2 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
          >
            Register your school
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="py-24 px-6 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 bg-violet-50 text-violet-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6 border border-violet-100">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
          30-day free trial — no credit card required
        </div>
        <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-6">
          Complete school management,<br />
          <span className="text-violet-600">all in one place</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          School MIS helps you manage students, teachers, finance, transport, and more —
          with powerful tools designed for African schools.
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => navigate("/register")}
            className="flex items-center gap-2 px-6 py-3 text-base font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-xl transition-colors shadow-lg shadow-violet-200"
          >
            Get started free
            <ArrowRight size={18} />
          </button>
          <button
            onClick={() => navigate("/login")}
            className="px-6 py-3 text-base font-semibold text-gray-700 hover:text-violet-600 border border-gray-200 hover:border-violet-200 rounded-xl transition-colors"
          >
            Sign in
          </button>
        </div>
      </section>

      {/* Features grid */}
      <section className="py-16 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">
            Everything your school needs
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {FEATURES.map(({ icon: Icon, label }) => (
              <div key={label} className="bg-white rounded-xl p-4 border border-gray-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                  <Icon size={16} className="text-violet-600" />
                </div>
                <span className="text-sm font-medium text-gray-700">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-2">Simple, transparent pricing</h2>
          <p className="text-gray-500 text-center mb-12">Start with a 30-day free trial on any plan.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {PLANS.map((plan) => (
              <div
                key={plan.key}
                className="relative rounded-2xl border p-6 flex flex-col"
                style={{
                  borderColor: plan.popular ? plan.color : "#E5E7EB",
                  boxShadow: plan.popular ? `0 0 0 2px ${plan.color}20` : undefined,
                }}
              >
                {plan.popular && (
                  <div
                    className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-xs font-bold text-white rounded-full"
                    style={{ backgroundColor: plan.color }}
                  >
                    Most Popular
                  </div>
                )}
                <div className="mb-4">
                  <p className="font-bold text-lg text-gray-900">{plan.label}</p>
                  <p className="text-2xl font-bold mt-1" style={{ color: plan.color }}>{plan.price}</p>
                </div>
                <ul className="space-y-2.5 flex-1 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                      <Check size={14} className="mt-0.5 flex-shrink-0" style={{ color: plan.color }} />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => navigate("/register")}
                  className="w-full py-2.5 text-sm font-semibold rounded-xl transition-colors"
                  style={{
                    backgroundColor: plan.popular ? plan.color : "transparent",
                    color: plan.popular ? "#fff" : plan.color,
                    border: plan.popular ? "none" : `1.5px solid ${plan.color}`,
                  }}
                >
                  Start free trial
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8 px-6 text-center text-sm text-gray-400">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-md bg-violet-600 flex items-center justify-center">
            <BookOpen size={12} className="text-white" />
          </div>
          <span className="font-semibold text-gray-700">School MIS</span>
        </div>
        <p>© {new Date().getFullYear()} School MIS. Built for African schools.</p>
      </footer>
    </div>
  );
}
