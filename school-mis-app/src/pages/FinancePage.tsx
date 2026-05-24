import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, DollarSign } from "lucide-react";
import { getPayments, getFinanceSummary, type Payment, type FinanceSummary } from "@/api/finance";
import StatCard from "@/components/ui/StatCard";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const fmt = (n: number) => `TZS ${n.toLocaleString()}`;

export default function FinancePage() {
  const [payments, setPayments]   = useState<Payment[]>([]);
  const [summary, setSummary]     = useState<FinanceSummary | null>(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([getPayments(100), getFinanceSummary()])
      .then(([p, s]) => { setPayments(p); setSummary(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Finance</h1>
        <p className="text-sm text-gray-500 mt-0.5">Fee collection and payments</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard title="Total Billed"  value={loading ? "—" : fmt(summary?.total_billed ?? 0)}    icon={DollarSign}  color="#7C3AED" />
        <StatCard title="Collected"     value={loading ? "—" : fmt(summary?.total_collected ?? 0)} icon={TrendingUp}  color="#059669" />
        <StatCard title="Outstanding"   value={loading ? "—" : fmt(summary?.balance ?? 0)}         icon={TrendingDown} color="#E11D48" />
      </div>

      <h2 className="text-base font-semibold text-gray-800 mb-3">Recent Payments</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Adm. No</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Method</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Reference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : payments.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={DollarSign} title="No payments recorded" description="Payments will appear here once recorded." />
                  </td>
                </tr>
              )
              : payments.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{p.student_name}</td>
                  <td className="px-4 py-3 text-gray-500">{p.admission_no}</td>
                  <td className="px-4 py-3 font-semibold text-emerald-700">{fmt(p.amount)}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{p.method}</td>
                  <td className="px-4 py-3 text-gray-600">{p.payment_date}</td>
                  <td className="px-4 py-3 text-gray-400">{p.reference || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
