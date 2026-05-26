import { useState, useEffect, useCallback } from "react";
import { Receipt, TrendingDown, TrendingUp, Plus } from "lucide-react";
import { getExpenses, getAccountingSummary, recordExpense, getExpenseCategories, type Expense, type AccountingSummary } from "@/api/accounting";
import StatCard from "@/components/ui/StatCard";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const fmt = (n: number) => `TZS ${(n ?? 0).toLocaleString()}`;
const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ExpenseDialog({ categories, onSave, onClose }: { categories: string[]; onSave: () => void; onClose: () => void }) {
  const DEFAULT_CATS = ["utilities", "maintenance", "salaries", "supplies", "transport", "other"];
  const cats = categories.length ? categories : DEFAULT_CATS;

  const [form, setForm] = useState({
    category:     cats[0] ?? "other",
    description:  "",
    amount:       "",
    expense_date: new Date().toISOString().slice(0, 10),
    vendor:       "",
    reference:    "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.description) { setError("Description is required."); return; }
    if (!form.amount || isNaN(Number(form.amount)) || Number(form.amount) <= 0) {
      setError("Enter a valid amount.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await recordExpense({
        category:     form.category,
        description:  form.description,
        amount:       Number(form.amount),
        expense_date: form.expense_date,
        vendor:       form.vendor    || undefined,
        reference:    form.reference || undefined,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to record expense.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Record Expense</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Category *">
            <select className={INPUT} value={form.category} onChange={(e) => set("category", e.target.value)}>
              {cats.map((c) => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
          </Field>
          <Field label="Description *">
            <input className={INPUT} value={form.description} onChange={(e) => set("description", e.target.value)} />
          </Field>
          <Field label="Amount (TZS) *">
            <input type="number" min="1" className={INPUT} value={form.amount} onChange={(e) => set("amount", e.target.value)} placeholder="0" />
          </Field>
          <Field label="Expense Date *">
            <input type="date" className={INPUT} value={form.expense_date} onChange={(e) => set("expense_date", e.target.value)} />
          </Field>
          <Field label="Vendor">
            <input className={INPUT} value={form.vendor} onChange={(e) => set("vendor", e.target.value)} />
          </Field>
          <Field label="Reference">
            <input className={INPUT} value={form.reference} onChange={(e) => set("reference", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Record Expense"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function AccountingPage() {
  const [expenses, setExpenses]     = useState<Expense[]>([]);
  const [summary, setSummary]       = useState<AccountingSummary | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading]       = useState(true);
  const [dialog, setDialog]         = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getExpenses(100), getAccountingSummary("month")])
      .then(([e, s]) => { setExpenses(e); setSummary(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    getExpenseCategories().then(setCategories).catch(() => {});
  }, [load]);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Accounting</h1>
          <p className="text-sm text-gray-500 mt-0.5">Expense tracking and financial summary</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Record Expense</Button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard title="This Month Income"   value={loading ? "—" : fmt(summary?.income   ?? 0)} icon={TrendingUp}  color="#059669" />
        <StatCard title="This Month Expenses" value={loading ? "—" : fmt(summary?.expenses ?? 0)} icon={TrendingDown} color="#E11D48" />
        <StatCard title="Net"                 value={loading ? "—" : fmt(summary?.net      ?? 0)} icon={Receipt}      color="#7C3AED" />
      </div>

      <h2 className="text-base font-semibold text-gray-800 mb-3">Recent Expenses</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
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
        </table></div>
      </div>

      {dialog && (
        <ExpenseDialog
          categories={categories}
          onSave={() => { setDialog(false); load(); }}
          onClose={() => setDialog(false)}
        />
      )}
    </div>
  );
}
