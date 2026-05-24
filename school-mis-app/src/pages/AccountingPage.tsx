import { useState, useEffect } from "react";
import { Receipt, TrendingDown } from "lucide-react";
import { getExpenses, getAccountingSummary, type Expense, type AccountingSummary } from "@/api/accounting";
import StatCard from "@/components/ui/StatCard";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const fmt = (n: number) => `TZS ${(n ?? 0).toLocaleString()}`;

export default function AccountingPage() {
  const [expenses, setExpenses]   = useState<Expense[]>([]);
  const [summary, setSummary]     = useState<AccountingSummary | null>(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([getExpenses(100), getAccountingSummary("month")])
      .then(([e, s]) => { setExpenses(e); setSummary(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Accounting</h1>
        <p className="text-sm text-gray-500 mt-0.5">Expense tracking and financial summary</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard title="This Month Income"   value={loading ? "—" : fmt(summary?.income ?? 0)}   icon={TrendingDown} color="#059669" />
        <StatCard title="This Month Expenses" value={loading ? "—" : fmt(summary?.expenses ?? 0)} icon={TrendingDown} color="#E11D48" />
        <StatCard title="Net"                 value={loading ? "—" : fmt(summary?.net ?? 0)}       icon={Receipt}      color="#7C3AED" />
      </div>

      <h2 className="text-base font-semibold text-gray-800 mb-3">Recent Expenses</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Vendor</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Reference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : expenses.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={Receipt} title="No expenses recorded" />
                  </td>
                </tr>
              )
              : expenses.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{e.expense_date}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">{e.category}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-800">{e.description}</td>
                  <td className="px-4 py-3 text-gray-500">{e.vendor || "—"}</td>
                  <td className="px-4 py-3 font-semibold text-red-700">{fmt(e.amount)}</td>
                  <td className="px-4 py-3 text-gray-400">{e.reference || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
