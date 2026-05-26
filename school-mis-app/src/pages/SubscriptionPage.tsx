import { useEffect, useState } from "react";
import {
  CheckCircle2, XCircle, Clock, AlertTriangle,
  Zap, RefreshCw, X, ChevronRight, Receipt, History,
  Shield, Users, GraduationCap, ExternalLink,
} from "lucide-react";
import {
  getPlans, getStatus, getInvoices, getHistory,
  createCheckout, manualActivate, cancelSubscription,
  type Plan, type SubscriptionStatus, type Invoice, type HistoryEntry,
} from "@/api/subscriptions";
import { getProviders } from "@/api/subscriptions";
import { useAuthStore } from "@/stores/authStore";
import PageHeader from "@/components/ui/PageHeader";

const FMT = new Intl.NumberFormat("sw-TZ", { style: "currency", currency: "TZS", maximumFractionDigits: 0 });
const fmtDate = (s?: string | null) => s ? new Date(s).toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }) : "—";
const fmtAmt  = (n: number) => FMT.format(n / 100);  // amounts stored as minor units

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    active:    { label: "Active",     cls: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: <CheckCircle2 size={12}/> },
    trialing:  { label: "Trial",      cls: "bg-blue-50 text-blue-700 border-blue-200",         icon: <Clock size={12}/> },
    past_due:  { label: "Past Due",   cls: "bg-amber-50 text-amber-700 border-amber-200",      icon: <AlertTriangle size={12}/> },
    expired:   { label: "Expired",    cls: "bg-red-50 text-red-700 border-red-200",            icon: <XCircle size={12}/> },
    canceled:  { label: "Canceled",   cls: "bg-gray-100 text-gray-600 border-gray-200",        icon: <XCircle size={12}/> },
    suspended: { label: "Suspended",  cls: "bg-red-50 text-red-700 border-red-200",            icon: <XCircle size={12}/> },
    pending:   { label: "Pending",    cls: "bg-gray-100 text-gray-500 border-gray-200",        icon: <Clock size={12}/> },
  };
  const c = cfg[status] ?? cfg.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ── Plan card ─────────────────────────────────────────────────────────────────
function PlanCard({
  plans, interval, currentPlan, onSelect,
}: {
  plans: Plan[]; interval: string; currentPlan: string; onSelect: (p: Plan) => void;
}) {
  const grouped: Record<string, Plan[]> = {};
  plans.forEach(p => { (grouped[p.name] = grouped[p.name] || []).push(p); });
  const names = ["basic", "standard", "premium"];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {names.map(name => {
        const group = grouped[name] || [];
        const plan  = group.find(p => p.billing_interval === interval) || group[0];
        if (!plan) return null;
        const isCurrent = plan.name === currentPlan;
        const isPopular = plan.name === "standard";

        return (
          <div
            key={name}
            className={[
              "relative rounded-2xl border-2 p-5 flex flex-col transition-all",
              isCurrent
                ? "border-violet-500 bg-violet-50 shadow-md"
                : "border-gray-200 bg-white hover:border-violet-300 hover:shadow-sm",
            ].join(" ")}
          >
            {isPopular && !isCurrent && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="bg-violet-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                  POPULAR
                </span>
              </div>
            )}
            {isCurrent && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                  <CheckCircle2 size={10}/> CURRENT
                </span>
              </div>
            )}

            <div className="mb-3">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: plan.color }} />
                <span className="font-bold text-gray-900">{plan.display_name}</span>
              </div>
              <p className="text-xs text-gray-500">{plan.description}</p>
            </div>

            <div className="mb-4">
              <span className="text-2xl font-extrabold text-gray-900">
                {FMT.format(plan.price_amount)}
              </span>
              <span className="text-xs text-gray-400 ml-1">/{plan.billing_interval === "yearly" ? "yr" : "mo"}</span>
              {plan.billing_interval === "yearly" && (
                <div className="text-xs text-emerald-600 font-medium mt-0.5">Save ~20% vs monthly</div>
              )}
            </div>

            <div className="mb-4 space-y-1 flex-1">
              <div className="flex items-center gap-2 text-xs text-gray-600">
                <Users size={11} className="flex-shrink-0 text-violet-500" />
                Up to {plan.max_users} staff accounts
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-600">
                <GraduationCap size={11} className="flex-shrink-0 text-violet-500" />
                Up to {plan.max_students.toLocaleString()} students
              </div>
              {plan.feature_list.slice(2).map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                  <CheckCircle2 size={11} className="flex-shrink-0 text-emerald-500" />
                  {f}
                </div>
              ))}
            </div>

            <button
              onClick={() => onSelect(plan)}
              disabled={isCurrent}
              className={[
                "w-full py-2 rounded-xl text-sm font-semibold transition-all flex items-center justify-center gap-1",
                isCurrent
                  ? "bg-emerald-100 text-emerald-700 cursor-default"
                  : "bg-violet-600 hover:bg-violet-700 text-white",
              ].join(" ")}
            >
              {isCurrent ? <><CheckCircle2 size={14}/>Current Plan</> : <>Subscribe<ChevronRight size={14}/></>}
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ── Checkout modal ────────────────────────────────────────────────────────────
function CheckoutModal({
  plan, interval, providers, onClose,
}: {
  plan: Plan; interval: string; providers: string[]; onClose: () => void;
}) {
  const [selectedProvider, setSelectedProvider] = useState(providers[0] || "");
  const [loading, setLoading]  = useState(false);
  const [error, setError]      = useState("");
  const [manualMode, setManualMode] = useState(false);
  const [manualDone, setManualDone] = useState(false);

  const providerInfo: Record<string, { label: string; logo: string; desc: string }> = {
    flutterwave: { label: "Flutterwave", logo: "🔶", desc: "M-Pesa, Tigo, Airtel, Card" },
    paystack:    { label: "Paystack",    logo: "💳", desc: "Card & Bank Transfer" },
  };

  const handleCheckout = async () => {
    setLoading(true);
    setError("");
    try {
      const redirectBack = `${window.location.origin}/subscription?verify=1`;
      const res = await createCheckout({
        plan_name: plan.name, interval, provider: selectedProvider,
        redirect_url: redirectBack,
      });
      window.location.href = res.checkout_url;
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to create checkout. Please try again.");
      setLoading(false);
    }
  };

  const handleManual = async () => {
    setLoading(true);
    setError("");
    try {
      await manualActivate({ plan_name: plan.name, interval });
      setManualDone(true);
      setTimeout(() => window.location.reload(), 1500);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Activation failed.");
    } finally {
      setLoading(false);
    }
  };

  if (manualDone) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="bg-white rounded-2xl p-8 text-center max-w-sm w-full">
          <CheckCircle2 size={48} className="mx-auto mb-3 text-emerald-500" />
          <p className="text-lg font-bold text-gray-900">Subscription Activated!</p>
          <p className="text-sm text-gray-500 mt-1">Reloading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Subscribing to</p>
            <p className="font-bold text-gray-900">{plan.display_name} — {interval}</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              {error}
            </div>
          )}

          {/* Amount */}
          <div className="bg-violet-50 border border-violet-100 rounded-xl px-4 py-3 flex justify-between items-center">
            <span className="text-sm text-violet-700 font-medium">Amount due</span>
            <span className="text-lg font-extrabold text-violet-900">{FMT.format(plan.price_amount)}</span>
          </div>

          {providers.length > 0 && !manualMode ? (
            <>
              <p className="text-sm font-medium text-gray-700">Select payment method</p>
              <div className="space-y-2">
                {providers.map(prov => {
                  const info = providerInfo[prov] || { label: prov, logo: "💰", desc: "" };
                  return (
                    <button
                      key={prov}
                      onClick={() => setSelectedProvider(prov)}
                      className={[
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left transition-all",
                        selectedProvider === prov
                          ? "border-violet-500 bg-violet-50"
                          : "border-gray-200 hover:border-gray-300",
                      ].join(" ")}
                    >
                      <span className="text-2xl">{info.logo}</span>
                      <div>
                        <p className="font-semibold text-sm text-gray-900">{info.label}</p>
                        <p className="text-xs text-gray-500">{info.desc}</p>
                      </div>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={handleCheckout}
                disabled={loading || !selectedProvider}
                className="w-full h-11 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors"
              >
                {loading ? <><RefreshCw size={15} className="animate-spin"/>Processing…</> : <><ExternalLink size={15}/>Proceed to Payment</>}
              </button>

              <button onClick={() => setManualMode(true)} className="w-full text-xs text-gray-400 hover:text-gray-600 text-center">
                Activate manually (offline payment)
              </button>
            </>
          ) : (
            <>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm text-amber-800">
                <p className="font-medium mb-1">Manual Activation</p>
                <p className="text-xs">Use this after confirming payment through bank transfer or other offline method. This is an admin action and is logged.</p>
              </div>
              <button
                onClick={handleManual}
                disabled={loading}
                className="w-full h-11 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center justify-center gap-2"
              >
                {loading ? <><RefreshCw size={15} className="animate-spin"/>Activating…</> : <>Activate Manually</>}
              </button>
              {providers.length > 0 && (
                <button onClick={() => setManualMode(false)} className="w-full text-xs text-gray-400 hover:text-gray-600 text-center">
                  ← Back to payment options
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SubscriptionPage() {
  const { user } = useAuthStore();
  const isAdmin  = user?.role === "admin";

  const [status,    setStatus]    = useState<SubscriptionStatus | null>(null);
  const [plans,     setPlans]     = useState<Plan[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [invoices,  setInvoices]  = useState<Invoice[]>([]);
  const [history,   setHistory]   = useState<HistoryEntry[]>([]);
  const [interval,  setInterval]  = useState<"monthly" | "yearly">("monthly");
  const [loading,   setLoading]   = useState(true);
  const [tab,       setTab]       = useState<"plans" | "invoices" | "history">("plans");
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    Promise.all([
      getStatus(), getPlans(), getProviders(), getInvoices(), getHistory(),
    ]).then(([s, p, prov, inv, hist]) => {
      setStatus(s);
      setPlans(p);
      setProviders(prov.providers);
      setInvoices(inv.items);
      setHistory(hist);
    }).finally(() => setLoading(false));

    // Handle redirect back from checkout
    const params = new URLSearchParams(window.location.search);
    if (params.get("verify") && params.get("tx_ref")) {
      // handled below
    }
  }, []);

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await cancelSubscription();
      setToast("Subscription will cancel at end of current period.");
      setCancelConfirm(false);
      const s = await getStatus();
      setStatus(s);
    } catch (e: any) {
      setToast(e?.response?.data?.detail ?? "Failed to cancel.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const planColor = status?.color || "#94A3B8";

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Subscription"
        subtitle="Manage your plan, billing, and payment history"
      />

      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-gray-900 text-white px-4 py-2 rounded-xl text-sm shadow-lg flex items-center gap-2">
          {toast}
          <button onClick={() => setToast("")}><X size={14}/></button>
        </div>
      )}

      {/* Current plan summary */}
      {status && (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl font-bold" style={{ backgroundColor: planColor }}>
                {status.display_name?.[0] ?? "?"}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-lg font-bold text-gray-900">{status.display_name} Plan</span>
                  <StatusBadge status={status.status} />
                </div>
                {status.current_period_end && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    {status.status === "active" ? "Renews" : "Expires"}: {fmtDate(status.current_period_end)}
                    {status.days_left != null && (
                      <span className={`ml-2 font-medium ${status.days_left <= 7 ? "text-red-600" : "text-gray-600"}`}>
                        ({status.days_left}d left)
                      </span>
                    )}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isAdmin && status.status === "active" && !cancelConfirm && (
                <button
                  onClick={() => setCancelConfirm(true)}
                  className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Cancel plan
                </button>
              )}
              {cancelConfirm && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-red-600">Confirm cancel?</span>
                  <button onClick={handleCancel} disabled={actionLoading} className="px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                    {actionLoading ? "…" : "Yes, cancel"}
                  </button>
                  <button onClick={() => setCancelConfirm(false)} className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg">
                    No
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Usage bars */}
          {(status.max_users || status.max_students) && (
            <div className="mt-4 grid grid-cols-2 gap-3">
              {status.max_users && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Staff accounts</span>
                    <span>/ {status.max_users}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-violet-500 rounded-full" style={{ width: "40%" }} />
                  </div>
                </div>
              )}
              {status.max_students && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Students</span>
                    <span>/ {status.max_students.toLocaleString()}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: "30%" }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Warning banner */}
          {status.warning && (
            <div className="mt-3 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
              <AlertTriangle size={15} className="flex-shrink-0" />
              {status.warning}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(["plans", "invoices", "history"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={[
              "px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors",
              tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700",
            ].join(" ")}
          >
            {t === "plans" && <span className="flex items-center gap-1.5"><Zap size={13}/>{t}</span>}
            {t === "invoices" && <span className="flex items-center gap-1.5"><Receipt size={13}/>{t}</span>}
            {t === "history" && <span className="flex items-center gap-1.5"><History size={13}/>{t}</span>}
          </button>
        ))}
      </div>

      {/* Plans tab */}
      {tab === "plans" && (
        <div className="space-y-4">
          {/* Billing interval toggle */}
          <div className="flex items-center gap-3">
            <span className={`text-sm ${interval === "monthly" ? "text-gray-900 font-medium" : "text-gray-400"}`}>Monthly</span>
            <button
              onClick={() => setInterval(i => i === "monthly" ? "yearly" : "monthly")}
              className={`relative w-10 h-5 rounded-full transition-colors ${interval === "yearly" ? "bg-violet-600" : "bg-gray-300"}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${interval === "yearly" ? "left-5" : "left-0.5"}`} />
            </button>
            <span className={`text-sm ${interval === "yearly" ? "text-gray-900 font-medium" : "text-gray-400"}`}>
              Yearly <span className="text-emerald-600 text-xs font-medium">Save 20%</span>
            </span>
          </div>

          {!isAdmin && (
            <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
              <Shield size={14}/> Only administrators can change the subscription plan.
            </div>
          )}

          <PlanCard
            plans={plans}
            interval={interval}
            currentPlan={status?.plan_name || ""}
            onSelect={isAdmin ? setSelectedPlan : () => {}}
          />

          {providers.length === 0 && isAdmin && (
            <div className="text-center py-4 text-sm text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-200">
              No payment providers are configured on the server.
              Set <code className="bg-gray-100 px-1 rounded">FLW_SECRET_KEY</code> or{" "}
              <code className="bg-gray-100 px-1 rounded">PAYSTACK_SECRET_KEY</code> environment variables to enable online payments.
              <br/>You can still activate manually below.
            </div>
          )}
        </div>
      )}

      {/* Invoices tab */}
      {tab === "invoices" && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {invoices.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Receipt size={32} className="mx-auto mb-2 opacity-30" />
              <p>No invoices yet</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left">Invoice #</th>
                  <th className="px-4 py-3 text-left">Period</th>
                  <th className="px-4 py-3 text-left">Amount</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Paid</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{inv.invoice_number || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">
                      {inv.billing_period_start ? `${fmtDate(inv.billing_period_start)} – ${fmtDate(inv.billing_period_end)}` : "—"}
                    </td>
                    <td className="px-4 py-3 font-medium">{fmtAmt(inv.amount_due)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        inv.status === "paid" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                      }`}>{inv.status}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(inv.paid_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* History tab */}
      {tab === "history" && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {history.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <History size={32} className="mx-auto mb-2 opacity-30" />
              <p>No history yet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {history.map(h => (
                <div key={h.id} className="px-4 py-3 flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-violet-400 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-gray-800 capitalize">
                        {h.event_type.replace(/_/g, " ")}
                      </span>
                      {h.to_status && <StatusBadge status={h.to_status} />}
                      {h.plan_display && (
                        <span className="text-xs text-gray-500">→ {h.plan_display}</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400">
                      {fmtDate(h.created_at)} · by {h.triggered_by}
                      {h.notes && ` · ${h.notes}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Checkout modal */}
      {selectedPlan && (
        <CheckoutModal
          plan={selectedPlan}
          interval={interval}
          providers={providers}
          onClose={() => setSelectedPlan(null)}
        />
      )}
    </div>
  );
}
