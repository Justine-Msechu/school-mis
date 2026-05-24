import { useState, useEffect, useCallback, useRef } from "react";
import { TrendingUp, TrendingDown, DollarSign, Plus, Search } from "lucide-react";
import { getPayments, getFinanceSummary, recordPayment, getStudentBill, type Payment, type FinanceSummary, type StudentBill } from "@/api/finance";
import { getStudents } from "@/api/students";
import { getFeeStructures, getFeeTypes, createFeeStructure, createFeeType, getAcademicYears, type FeeStructure, type FeeType, type AcademicYear } from "@/api/settings";
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

type Tab = "payments" | "fees" | "student-bill";

// ── Payment dialog ──────────────────────────────────────────────────────────

function PaymentDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    admission_no:  "",
    student_id:    null as number | null,
    student_name:  "",
    amount:        "",
    payment_date:  new Date().toISOString().slice(0, 10),
    method:        "cash",
    reference:     "",
    notes:         "",
  });
  const [lookupState, setLookupState] = useState<"idle" | "loading" | "found" | "error">("idle");
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const lookupStudent = async () => {
    if (!form.admission_no.trim()) return;
    setLookupState("loading");
    try {
      const res = await getStudents({ search: form.admission_no.trim(), per_page: 10 });
      const student = res.items.find((s) => s.admission_no === form.admission_no.trim());
      if (student) {
        setForm((f) => ({ ...f, student_id: student.id, student_name: `${student.first_name} ${student.last_name}` }));
        setLookupState("found");
      } else {
        setForm((f) => ({ ...f, student_id: null, student_name: "" }));
        setLookupState("error");
      }
    } catch { setLookupState("error"); }
  };

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.student_id) { setError("Please look up a valid student first."); return; }
    if (!form.amount || isNaN(Number(form.amount)) || Number(form.amount) <= 0) { setError("Enter a valid amount."); return; }
    setSaving(true); setError("");
    try {
      await recordPayment({ student_id: form.student_id, amount: Number(form.amount), payment_date: form.payment_date, method: form.method, reference: form.reference || undefined, notes: form.notes || undefined });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to record payment.");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Record Payment</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Admission Number *">
            <div className="flex gap-2">
              <input className={INPUT} value={form.admission_no} placeholder="e.g. ADM001"
                onChange={(e) => { setLookupState("idle"); setForm((f) => ({ ...f, admission_no: e.target.value, student_id: null, student_name: "" })); }}
                onKeyDown={(e) => e.key === "Enter" && lookupStudent()} />
              <Button variant="outline" size="sm" onClick={lookupStudent} disabled={lookupState === "loading"}>{lookupState === "loading" ? "…" : "Find"}</Button>
            </div>
            {lookupState === "found" && <p className="text-xs text-green-600 mt-1">✓ {form.student_name}</p>}
            {lookupState === "error"  && <p className="text-xs text-red-600 mt-1">Student not found</p>}
          </Field>
          <Field label="Amount (TZS) *"><input type="number" min="1" className={INPUT} value={form.amount} onChange={(e) => set("amount", e.target.value)} placeholder="0" /></Field>
          <Field label="Payment Date *"><input type="date" className={INPUT} value={form.payment_date} onChange={(e) => set("payment_date", e.target.value)} /></Field>
          <Field label="Method">
            <select className={INPUT} value={form.method} onChange={(e) => set("method", e.target.value)}>
              <option value="cash">Cash</option>
              <option value="mpesa">M-Pesa</option>
              <option value="bank">Bank Transfer</option>
              <option value="cheque">Cheque</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Reference"><input className={INPUT} value={form.reference} onChange={(e) => set("reference", e.target.value)} placeholder="Transaction ref…" /></Field>
          <Field label="Notes"><input className={INPUT} value={form.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Record Payment"}</Button>
        </div>
      </div>
    </div>
  );
}

// ── Fee structure dialog ────────────────────────────────────────────────────

function FeeStructureDialog({ feeTypes, years, onSave, onClose }: {
  feeTypes: FeeType[]; years: AcademicYear[]; onSave: () => void; onClose: () => void;
}) {
  const [form, setForm] = useState({
    fee_type_id:      feeTypes[0]?.id?.toString() ?? "",
    academic_year_id: years.find((y) => y.is_current)?.id?.toString() ?? years[0]?.id?.toString() ?? "",
    amount:           "",
    due_date:         "",
  });
  const [newFeeType, setNewFeeType] = useState("");
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.amount || Number(form.amount) <= 0) { setError("Enter a valid amount."); return; }
    if (!form.fee_type_id) { setError("Select a fee type."); return; }
    if (!form.academic_year_id) { setError("Select an academic year."); return; }
    setSaving(true); setError("");
    try {
      let typeId = Number(form.fee_type_id);
      if (!typeId && newFeeType.trim()) {
        const t = await createFeeType({ name: newFeeType.trim() });
        typeId = t.id;
      }
      await createFeeStructure({ fee_type_id: typeId, academic_year_id: Number(form.academic_year_id), amount: Number(form.amount), due_date: form.due_date || undefined });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save fee structure.");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Add Fee Structure</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Fee Type *">
            <select className={INPUT} value={form.fee_type_id} onChange={(e) => set("fee_type_id", e.target.value)}>
              <option value="">— Select —</option>
              {feeTypes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              <option value="__new__">+ New fee type…</option>
            </select>
          </Field>
          {form.fee_type_id === "__new__" && (
            <Field label="New Fee Type Name *">
              <input className={INPUT} value={newFeeType} onChange={(e) => setNewFeeType(e.target.value)} placeholder="e.g. Tuition Fee" />
            </Field>
          )}
          <Field label="Academic Year *">
            <select className={INPUT} value={form.academic_year_id} onChange={(e) => set("academic_year_id", e.target.value)}>
              {years.map((y) => <option key={y.id} value={y.id}>{y.label}{y.is_current ? " (current)" : ""}</option>)}
            </select>
          </Field>
          <Field label="Amount (TZS) *"><input type="number" min="1" className={INPUT} value={form.amount} onChange={(e) => set("amount", e.target.value)} placeholder="0" /></Field>
          <Field label="Due Date"><input type="date" className={INPUT} value={form.due_date} onChange={(e) => set("due_date", e.target.value)} /></Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

// ── Student Bill lookup ─────────────────────────────────────────────────────

function StudentBillPanel() {
  const [admNo, setAdmNo]   = useState("");
  const [bill, setBill]     = useState<StudentBill | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const lookup = async () => {
    if (!admNo.trim()) return;
    setLoading(true); setError(""); setBill(null);
    try {
      const data = await getStudentBill(undefined, admNo.trim());
      setBill(data);
    } catch { setError("Student not found or no billing data."); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <div className="relative max-w-xs flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={admNo}
            onChange={(e) => setAdmNo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && lookup()}
            placeholder="Admission number…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <Button variant="primary" onClick={lookup} disabled={loading}>{loading ? "Looking up…" : "Look Up"}</Button>
      </div>

      {error && <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

      {bill && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
              <div className="text-xs font-medium text-violet-600">Total Billed</div>
              <div className="text-lg font-bold text-violet-900 mt-1">{fmt(bill.total_billed)}</div>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <div className="text-xs font-medium text-emerald-600">Total Paid</div>
              <div className="text-lg font-bold text-emerald-900 mt-1">{fmt(bill.total_paid)}</div>
            </div>
            <div className={`border rounded-xl p-4 ${bill.balance > 0 ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
              <div className={`text-xs font-medium ${bill.balance > 0 ? "text-red-600" : "text-gray-500"}`}>Balance Due</div>
              <div className={`text-lg font-bold mt-1 ${bill.balance > 0 ? "text-red-900" : "text-gray-700"}`}>{fmt(bill.balance)}</div>
            </div>
          </div>

          {bill.bills.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700">Bills</h3>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase"><th className="px-4 py-2.5">Fee Type</th><th className="px-4 py-2.5">Amount</th><th className="px-4 py-2.5">Due Date</th></tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {bill.bills.map((b) => (
                      <tr key={b.id}><td className="px-4 py-2.5 text-gray-800">{b.fee_type_name}</td><td className="px-4 py-2.5 font-medium text-gray-900">{fmt(b.amount)}</td><td className="px-4 py-2.5 text-gray-500">{b.due_date || "—"}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {bill.payments.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700">Payments</h3>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase"><th className="px-4 py-2.5">Date</th><th className="px-4 py-2.5">Amount</th><th className="px-4 py-2.5">Method</th><th className="px-4 py-2.5">Reference</th></tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {bill.payments.map((p) => (
                      <tr key={p.id}><td className="px-4 py-2.5 text-gray-600">{p.payment_date}</td><td className="px-4 py-2.5 font-medium text-emerald-700">{fmt(p.amount)}</td><td className="px-4 py-2.5 capitalize text-gray-600">{p.method}</td><td className="px-4 py-2.5 text-gray-400">{p.reference || "—"}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function FinancePage() {
  const [tab, setTab]           = useState<Tab>("payments");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [summary, setSummary]   = useState<FinanceSummary | null>(null);
  const [feeStructures, setFeeStructures] = useState<FeeStructure[]>([]);
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [years, setYears]       = useState<AcademicYear[]>([]);
  const [loading, setLoading]   = useState(true);
  const [paymentDialog, setPaymentDialog] = useState(false);
  const [feeDialog, setFeeDialog]         = useState(false);

  const paymentsLoaded = useRef(false);
  const feesLoaded     = useRef(false);

  const loadPayments = useCallback(() => {
    if (!paymentsLoaded.current) setLoading(true);
    Promise.all([getPayments(100), getFinanceSummary()])
      .then(([p, s]) => { setPayments(p); setSummary(s); paymentsLoaded.current = true; })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  const loadFees = useCallback(() => {
    if (!feesLoaded.current) setLoading(true);
    Promise.all([getFeeStructures(), getFeeTypes(), getAcademicYears()])
      .then(([fs, ft, ay]) => { setFeeStructures(fs); setFeeTypes(ft); setYears(ay); feesLoaded.current = true; })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab === "payments") loadPayments();
    else if (tab === "fees") loadFees();
    else setLoading(false);
  }, [tab, loadPayments, loadFees]);

  const TABS = [
    { key: "payments" as Tab,    label: "Payments" },
    { key: "fees" as Tab,        label: "Fee Structures" },
    { key: "student-bill" as Tab, label: "Student Bill" },
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Finance</h1>
          <p className="text-sm text-gray-500 mt-0.5">Fee collection and payments</p>
        </div>
        {tab === "payments" && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setPaymentDialog(true)}>Record Payment</Button>
        )}
        {tab === "fees" && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setFeeDialog(true)}>Add Fee Structure</Button>
        )}
      </div>

      {tab === "payments" && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard title="Total Billed"  value={loading ? "—" : fmt(summary?.total_billed    ?? 0)} icon={DollarSign}  color="#7C3AED" />
          <StatCard title="Collected"     value={loading ? "—" : fmt(summary?.total_collected ?? 0)} icon={TrendingUp}  color="#059669" />
          <StatCard title="Outstanding"   value={loading ? "—" : fmt(summary?.balance         ?? 0)} icon={TrendingDown} color="#E11D48" />
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "payments" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th><th className="px-4 py-3">Adm. No</th>
              <th className="px-4 py-3">Amount</th><th className="px-4 py-3">Method</th>
              <th className="px-4 py-3">Date</th><th className="px-4 py-3">Reference</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                : payments.length === 0
                ? <tr><td colSpan={6} className="py-16"><EmptyState icon={DollarSign} title="No payments recorded" /></td></tr>
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
      )}

      {tab === "fees" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Fee Type</th><th className="px-4 py-3">Academic Year</th>
              <th className="px-4 py-3">Amount</th><th className="px-4 py-3">Due Date</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
                : feeStructures.length === 0
                ? <tr><td colSpan={4} className="py-16"><EmptyState icon={DollarSign} title="No fee structures" description="Add fee structures to bill students." /></td></tr>
                : feeStructures.map((fs) => (
                  <tr key={fs.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{fs.fee_type_name}</td>
                    <td className="px-4 py-3 text-gray-600">{fs.year_label}</td>
                    <td className="px-4 py-3 font-semibold text-violet-700">{fmt(fs.amount)}</td>
                    <td className="px-4 py-3 text-gray-500">{fs.due_date || "—"}</td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {tab === "student-bill" && <StudentBillPanel />}

      {paymentDialog && (
        <PaymentDialog onSave={() => { setPaymentDialog(false); loadPayments(); }} onClose={() => setPaymentDialog(false)} />
      )}
      {feeDialog && years.length > 0 && (
        <FeeStructureDialog feeTypes={feeTypes} years={years} onSave={() => { setFeeDialog(false); loadFees(); }} onClose={() => setFeeDialog(false)} />
      )}
    </div>
  );
}
