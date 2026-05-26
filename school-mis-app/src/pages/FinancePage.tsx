import { useState, useEffect, useCallback, useRef } from "react";
import { TrendingUp, TrendingDown, DollarSign, Plus, Search, Download, AlertTriangle, Zap } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { getPayments, getFinanceSummary, recordPayment, getStudentBill, getOutstandingDebtors, type Payment, type FinanceSummary, type StudentBill, type DebtorRow } from "@/api/finance";
import { getStudents } from "@/api/students";
import { getFeeStructures, getFeeTypes, createFeeStructure, createFeeType, getAcademicYears, type FeeStructure, type FeeType, type AcademicYear } from "@/api/settings";
import { getClasses } from "@/api/grades";
import { useAuthStore } from "@/stores/authStore";
import { useToast } from "@/components/ui/Toast";
import StatCard from "@/components/ui/StatCard";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import api from "@/api/client";

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

type Tab = "payments" | "fees" | "student-bill" | "outstanding";

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

// ── Generate Bills dialog ───────────────────────────────────────────────────

function GenerateBillsDialog({ years, onDone, onClose }: {
  years: AcademicYear[];
  onDone: () => void;
  onClose: () => void;
}) {
  const toast = useToast();
  const [classes, setClasses]   = useState<{ id: number; name: string }[]>([]);
  const [yearId, setYearId]     = useState(years.find((y) => y.is_current)?.id?.toString() ?? years[0]?.id?.toString() ?? "");
  const [classId, setClassId]   = useState("");
  const [running, setRunning]   = useState(false);
  const [result, setResult]     = useState<{ created: number; skipped: number } | null>(null);

  useEffect(() => {
    getClasses().then(setClasses).catch(() => {});
  }, []);

  const run = async () => {
    if (!yearId) return;
    setRunning(true);
    try {
      const { data } = await api.post("/finance/billing/generate", {
        academic_year_id: Number(yearId),
        class_id: classId ? Number(classId) : null,
      });
      setResult(data);
      toast.success(`${data.created} bill${data.created !== 1 ? "s" : ""} created`);
      onDone();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Billing failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Generate Student Bills</h2>
        <p className="text-sm text-gray-500 mb-5">
          Creates one bill per student per fee structure. Already-billed combinations are skipped automatically.
        </p>

        {result ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-emerald-700">{result.created}</div>
                <div className="text-xs text-emerald-600 mt-1">Bills created</div>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-gray-500">{result.skipped}</div>
                <div className="text-xs text-gray-400 mt-1">Already existed</div>
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <Button variant="primary" onClick={onClose}>Done</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="Academic Year *">
              <select className={INPUT} value={yearId} onChange={(e) => setYearId(e.target.value)}>
                {years.map((y) => (
                  <option key={y.id} value={y.id}>{y.label}{y.is_current ? " (current)" : ""}</option>
                ))}
              </select>
            </Field>
            <Field label="Class (leave blank for all classes)">
              <select className={INPUT} value={classId} onChange={(e) => setClassId(e.target.value)}>
                <option value="">All classes</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-2 text-xs text-amber-800">
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5 text-amber-500" />
              This will charge all active students based on the fee structures defined for the selected year. Existing bills are never duplicated.
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button variant="primary" icon={<Zap size={14} />} onClick={run} disabled={running || !yearId}>
                {running ? "Generating…" : "Generate Bills"}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Outstanding debtors tab ─────────────────────────────────────────────────

function OutstandingTab() {
  const [debtors, setDebtors]   = useState<DebtorRow[]>([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState("");

  useEffect(() => {
    setLoading(true);
    getOutstandingDebtors()
      .then(setDebtors)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = debtors.filter((d) => {
    const q = search.toLowerCase();
    return (
      d.student_name.toLowerCase().includes(q) ||
      d.admission_no.toLowerCase().includes(q) ||
      (d.class_name ?? "").toLowerCase().includes(q)
    );
  });

  const totalBalance = debtors.reduce((s, d) => s + d.balance, 0);

  return (
    <div>
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="text-xs font-medium text-red-600">Students with Debt</div>
          <div className="text-2xl font-bold text-red-900 mt-1">{loading ? "—" : debtors.length}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="text-xs font-medium text-red-600">Total Outstanding</div>
          <div className="text-2xl font-bold text-red-900 mt-1">{loading ? "—" : fmt(totalBalance)}</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle size={20} className="text-amber-500 flex-shrink-0" />
          <p className="text-xs text-amber-800">These students have unpaid or partially paid bills for the selected year.</p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="relative max-w-xs flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, adm no, class…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        {filtered.length > 0 && (
          <button
            onClick={() => downloadCSV(
              "Outstanding Debtors",
              ["Student", "Adm No", "Class", "Billed (TZS)", "Paid (TZS)", "Balance (TZS)"],
              filtered.map((d) => [d.student_name, d.admission_no, d.class_name ?? "", d.total_billed, d.total_paid, d.balance])
            )}
            className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download size={14} /> Export
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Adm. No</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3 text-right">Billed</th>
              <th className="px-4 py-3 text-right">Paid</th>
              <th className="px-4 py-3 text-right">Balance Due</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : filtered.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={DollarSign} title="No outstanding debts" description={search ? "No matches for your search." : "All students are fully paid up."} />
                  </td>
                </tr>
              )
              : filtered.map((d) => (
                <tr key={d.student_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{d.student_name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{d.admission_no}</td>
                  <td className="px-4 py-3 text-gray-600">{d.class_name ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{fmt(d.total_billed)}</td>
                  <td className="px-4 py-3 text-right text-emerald-700">{fmt(d.total_paid)}</td>
                  <td className="px-4 py-3 text-right font-bold text-red-600">{fmt(d.balance)}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function FinancePage() {
  const { can }                 = useAuthStore();
  const [tab, setTab]           = useState<Tab>("payments");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [summary, setSummary]   = useState<FinanceSummary | null>(null);
  const [feeStructures, setFeeStructures] = useState<FeeStructure[]>([]);
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [years, setYears]       = useState<AcademicYear[]>([]);
  const [loading, setLoading]   = useState(true);
  const [paymentDialog, setPaymentDialog]     = useState(false);
  const [feeDialog, setFeeDialog]             = useState(false);
  const [billingDialog, setBillingDialog]     = useState(false);

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
    else setLoading(false); // student-bill and outstanding manage their own loading
  }, [tab, loadPayments, loadFees]);

  const TABS = [
    { key: "payments" as Tab,     label: "Payments" },
    { key: "fees" as Tab,         label: "Fee Structures" },
    { key: "student-bill" as Tab, label: "Student Bill" },
    { key: "outstanding" as Tab,  label: "Outstanding Debts" },
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Finance</h1>
          <p className="text-sm text-gray-500 mt-0.5">Fee collection and payments</p>
        </div>
        {tab === "payments" && (
          <div className="flex gap-2">
            {payments.length > 0 && (
              <button
                onClick={() => downloadCSV("Payments", ["Student","Adm No","Amount (TZS)","Method","Date","Reference"],
                  payments.map((p: any) => [p.student_name, p.admission_no, p.amount_paid ?? p.amount, p.payment_method ?? "", p.payment_date ?? p.created_at?.slice(0,10), p.reference ?? ""]))}
                className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Download size={14} /> Export
              </button>
            )}
            <Button variant="primary" icon={<Plus size={15} />} onClick={() => setPaymentDialog(true)}>Record Payment</Button>
          </div>
        )}
        {tab === "fees" && (
          <div className="flex gap-2">
            {can("finance.billing.generate") && years.length > 0 && (
              <Button variant="outline" icon={<Zap size={14} />} onClick={() => setBillingDialog(true)}>Generate Bills</Button>
            )}
            <Button variant="primary" icon={<Plus size={15} />} onClick={() => setFeeDialog(true)}>Add Fee Structure</Button>
          </div>
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
              <th className="px-4 py-3">Fee Type</th>
              <th className="px-4 py-3">Applies To</th>
              <th className="px-4 py-3">Academic Year</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Due Date</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
                : feeStructures.length === 0
                ? <tr><td colSpan={5} className="py-16"><EmptyState icon={DollarSign} title="No fee structures" description="Add fee structures to bill students." /></td></tr>
                : feeStructures.map((fs) => (
                  <tr key={fs.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{fs.fee_type_name}</td>
                    <td className="px-4 py-3">
                      {fs.class_name
                        ? <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded text-xs font-medium">{fs.class_name}</span>
                        : <span className="text-gray-400 text-xs">All classes</span>
                      }
                    </td>
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
      {tab === "outstanding"  && <OutstandingTab />}

      {paymentDialog && (
        <PaymentDialog onSave={() => { setPaymentDialog(false); loadPayments(); }} onClose={() => setPaymentDialog(false)} />
      )}
      {feeDialog && years.length > 0 && (
        <FeeStructureDialog feeTypes={feeTypes} years={years} onSave={() => { setFeeDialog(false); loadFees(); }} onClose={() => setFeeDialog(false)} />
      )}
      {billingDialog && years.length > 0 && (
        <GenerateBillsDialog years={years} onDone={loadFees} onClose={() => setBillingDialog(false)} />
      )}
    </div>
  );
}
