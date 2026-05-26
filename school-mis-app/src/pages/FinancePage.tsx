import { useState, useEffect, useCallback, useRef } from "react";
import { TrendingUp, TrendingDown, DollarSign, Plus, Search, Download, AlertTriangle, Zap, Lock, Unlock, ArrowRightLeft, Clock, CheckCircle, XCircle, Trash2, FileText, ShieldCheck, Copy } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { getPayments, getFinanceSummary, recordPayment, getStudentBill, getOutstandingDebtors, createWaiver, deleteWaiver, carryForward, getLockedPeriods, lockPeriod, unlockPeriod, getLateFeeRules, createLateFeeRule, deleteLateFeeRule, applyLateFees, getInstallments, createInstallmentPlan, getPendingApprovals, approveAction, rejectAction, type Payment, type FinanceSummary, type StudentBill, type DebtorRow, type WaiverRecord, type LockedPeriod, type LateFeeRule, type InstallmentRow, type PendingApproval } from "@/api/finance";
import { getInvoices, createInvoice, approveInvoice, issueControlNumber, payInvoice, voidInvoice, getInvoiceAudit, type Invoice, type AuditEntry } from "@/api/invoices";
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

type Tab = "payments" | "fees" | "student-bill" | "outstanding" | "manage" | "approvals" | "invoices";

// ── Shared student search with name dropdown ────────────────────────────────

interface SelectedStudent { id: number; name: string; admission_no: string; class_name?: string | null }

function StudentSearch({
  value, onChange, placeholder = "Search by name or admission no…",
}: {
  value: SelectedStudent | null;
  onChange: (s: SelectedStudent | null) => void;
  placeholder?: string;
}) {
  const [query, setQuery]       = useState(value ? `${value.name} (${value.admission_no})` : "");
  const [results, setResults]   = useState<SelectedStudent[]>([]);
  const [open, setOpen]         = useState(false);
  const [loading, setLoading]   = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const search = useCallback(async (q: string) => {
    if (q.trim().length < 2) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const res = await getStudents({ search: q.trim(), per_page: 8 });
      setResults(res.items.map((s) => ({
        id: s.id,
        name: `${s.first_name} ${s.last_name}`,
        admission_no: s.admission_no,
        class_name: s.class_name ?? null,
      })));
      setOpen(true);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, []);

  // Debounce
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const handleInput = (q: string) => {
    setQuery(q);
    onChange(null);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => search(q), 280);
  };

  const select = (s: SelectedStudent) => {
    setQuery(`${s.name} (${s.admission_no})`);
    onChange(s);
    setOpen(false);
    setResults([]);
  };

  const clear = () => { setQuery(""); onChange(null); setResults([]); setOpen(false); };

  return (
    <div ref={ref} className="relative">
      <div className="relative">
        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        <input
          className={`${INPUT} pl-8 pr-7`}
          value={query}
          onChange={(e) => handleInput(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={placeholder}
          autoComplete="off"
        />
        {loading && (
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs animate-pulse">…</span>
        )}
        {!loading && value && (
          <button onClick={clear} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-600 text-base leading-none">×</button>
        )}
      </div>
      {value && (
        <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500" />
          {value.name} · {value.admission_no}{value.class_name ? ` · ${value.class_name}` : ""}
        </p>
      )}
      {open && results.length > 0 && (
        <div className="absolute z-50 top-full mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          {results.map((s) => (
            <button
              key={s.id}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); select(s); }}
              className="w-full text-left px-3 py-2 hover:bg-violet-50 transition-colors border-b border-gray-50 last:border-0"
            >
              <span className="font-medium text-gray-900 text-sm">{s.name}</span>
              <span className="text-gray-400 text-xs ml-2">{s.admission_no}</span>
              {s.class_name && <span className="text-gray-400 text-xs ml-1">· {s.class_name}</span>}
            </button>
          ))}
        </div>
      )}
      {open && !loading && results.length === 0 && query.trim().length >= 2 && (
        <div className="absolute z-50 top-full mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg px-3 py-2 text-sm text-gray-400">
          No students found
        </div>
      )}
    </div>
  );
}

// ── Payment dialog ──────────────────────────────────────────────────────────

function PaymentDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [student, setStudent]   = useState<SelectedStudent | null>(null);
  const [amount, setAmount]     = useState("");
  const [date, setDate]         = useState(new Date().toISOString().slice(0, 10));
  const [method, setMethod]     = useState("cash");
  const [refNo, setRefNo]       = useState("");
  const [notes, setNotes]       = useState("");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  const submit = async () => {
    if (!student) { setError("Please select a student first."); return; }
    if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) { setError("Enter a valid amount."); return; }
    setSaving(true); setError("");
    try {
      await recordPayment({
        student_id:   student.id,
        amount:       Number(amount),
        payment_date: date,
        method,
        reference_no: refNo || undefined,
        notes:        notes || undefined,
      });
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
          <Field label="Student *">
            <StudentSearch value={student} onChange={setStudent} />
          </Field>
          <Field label="Amount (TZS) *">
            <input type="number" min="1" className={INPUT} value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0" />
          </Field>
          <Field label="Payment Date *">
            <input type="date" className={INPUT} value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <Field label="Method">
            <select className={INPUT} value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="cash">Cash</option>
              <option value="mpesa">M-Pesa</option>
              <option value="bank">Bank Transfer</option>
              <option value="cheque">Cheque</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Reference No">
            <input className={INPUT} value={refNo} onChange={(e) => setRefNo(e.target.value)} placeholder="Transaction ref…" />
          </Field>
          <Field label="Notes">
            <input className={INPUT} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
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
    scope:            "all" as "all" | "class" | "student",
    class_id:         "",
    student_type:     "" as string,
    term:             "" as string,
  });
  const [selectedStudent, setSelectedStudent] = useState<SelectedStudent | null>(null);
  const [classes, setClasses]   = useState<{ id: number; name: string }[]>([]);
  const [newFeeType, setNewFeeType] = useState("");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  useEffect(() => { getClasses().then(setClasses).catch(() => {}); }, []);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.amount || Number(form.amount) <= 0) { setError("Enter a valid amount."); return; }
    if (!form.fee_type_id) { setError("Select a fee type."); return; }
    if (!form.academic_year_id) { setError("Select an academic year."); return; }
    if (form.scope === "class" && !form.class_id) { setError("Select a class."); return; }
    if (form.scope === "student" && !selectedStudent) { setError("Select a student first."); return; }
    setSaving(true); setError("");
    try {
      let typeId = Number(form.fee_type_id);
      if (!typeId && newFeeType.trim()) {
        const t = await createFeeType({ name: newFeeType.trim() });
        typeId = t.id;
      }
      await createFeeStructure({
        fee_type_id:      typeId,
        academic_year_id: Number(form.academic_year_id),
        amount:           Number(form.amount),
        due_date:         form.due_date || undefined,
        class_id:         form.scope === "class"   ? Number(form.class_id) : null,
        student_id:       form.scope === "student" ? selectedStudent!.id   : null,
        student_type:     form.student_type || null,
        term:             form.term ? Number(form.term) : undefined,
      });
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
          <Field label="Applies To *">
            <select className={INPUT} value={form.scope} onChange={(e) => set("scope", e.target.value)}>
              <option value="all">All Students</option>
              <option value="class">Specific Class</option>
              <option value="student">Specific Student</option>
            </select>
          </Field>
          {form.scope === "class" && (
            <Field label="Class *">
              <select className={INPUT} value={form.class_id} onChange={(e) => set("class_id", e.target.value)}>
                <option value="">— Select class —</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
          )}
          {form.scope === "student" && (
            <Field label="Student *">
              <StudentSearch value={selectedStudent} onChange={setSelectedStudent} />
            </Field>
          )}
          <Field label="Student Type">
            <select className={INPUT} value={form.student_type} onChange={(e) => set("student_type", e.target.value)}>
              <option value="">All (Day &amp; Boarding)</option>
              <option value="Day">Day Scholars only</option>
              <option value="Boarding">Boarding students only</option>
            </select>
          </Field>
          <Field label="Term">
            <select className={INPUT} value={form.term} onChange={(e) => set("term", e.target.value)}>
              <option value="">All Terms</option>
              <option value="1">Term 1</option>
              <option value="2">Term 2</option>
              <option value="3">Term 3</option>
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

const WAIVER_TYPES = [
  { value: "scholarship",       label: "Scholarship" },
  { value: "orphan_exemption",  label: "Orphan Exemption" },
  { value: "partial_discount",  label: "Partial Discount" },
  { value: "staff_child",       label: "Staff Child" },
  { value: "other",             label: "Other" },
];

function WaiverDialog({ bill, studentId, onSave, onClose }: {
  bill: StudentBill; studentId: number; onSave: () => void; onClose: () => void;
}) {
  const toast = useToast();
  const [form, setForm] = useState({ bill_id: "", waiver_type: "scholarship", discount_percent: "100", reason: "" });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    const pct = Number(form.discount_percent);
    if (!pct || pct <= 0 || pct > 100) { toast.error("Discount must be 1–100%"); return; }
    setSaving(true);
    try {
      await createWaiver({
        student_id:       studentId,
        bill_id:          form.bill_id ? Number(form.bill_id) : null,
        waiver_type:      form.waiver_type,
        discount_percent: pct,
        reason:           form.reason || undefined,
      });
      toast.success("Waiver granted");
      onSave();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Failed to grant waiver");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-base font-bold text-gray-900 mb-4">Grant Waiver</h2>
        <div className="space-y-3">
          <Field label="Apply to Bill (leave blank for all bills)">
            <select className={INPUT} value={form.bill_id} onChange={(e) => set("bill_id", e.target.value)}>
              <option value="">All bills</option>
              {bill.bills.map((b) => (
                <option key={b.id} value={b.id}>{b.fee_type_name} — {fmt(b.amount_due)}</option>
              ))}
            </select>
          </Field>
          <Field label="Waiver Type">
            <select className={INPUT} value={form.waiver_type} onChange={(e) => set("waiver_type", e.target.value)}>
              {WAIVER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
          <Field label="Discount %">
            <input type="number" min="1" max="100" className={INPUT} value={form.discount_percent} onChange={(e) => set("discount_percent", e.target.value)} />
          </Field>
          <Field label="Reason">
            <input className={INPUT} value={form.reason} onChange={(e) => set("reason", e.target.value)} placeholder="e.g. Government scholarship" />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Grant Waiver"}</Button>
        </div>
      </div>
    </div>
  );
}

function StudentBillPanel() {
  const { can }                 = useAuthStore();
  const toast                   = useToast();
  const [selected, setSelected] = useState<SelectedStudent | null>(null);
  const [bill, setBill]         = useState<StudentBill | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [waiverOpen, setWaiverOpen] = useState(false);

  const lookup = useCallback(async (s: SelectedStudent | null) => {
    if (!s) { setBill(null); return; }
    setLoading(true); setError(""); setBill(null);
    try {
      const data = await getStudentBill(s.id);
      setBill(data);
    } catch { setError("No billing data found for this student."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { lookup(selected); }, [selected, lookup]);

  const handleRemoveWaiver = async (id: number) => {
    if (!confirm("Remove this waiver? The discount will be reversed.")) return;
    try {
      await deleteWaiver(id);
      toast.success("Waiver removed");
      lookup(selected);
    } catch { toast.error("Failed to remove waiver"); }
  };

  return (
    <div>
      <div className="max-w-sm mb-5">
        <StudentSearch value={selected} onChange={setSelected} placeholder="Search student by name or admission no…" />
      </div>

      {loading && <div className="h-20 bg-gray-50 rounded-xl animate-pulse mb-4" />}
      {error && <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

      {bill && (
        <div className="space-y-5">
          {/* Summary cards */}
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-violet-50 border border-violet-200 rounded-xl p-3">
              <div className="text-xs font-medium text-violet-600">Total Billed</div>
              <div className="text-base font-bold text-violet-900 mt-0.5">{fmt(bill.total_billed)}</div>
            </div>
            {bill.total_discount > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                <div className="text-xs font-medium text-amber-600">Discount/Waiver</div>
                <div className="text-base font-bold text-amber-900 mt-0.5">- {fmt(bill.total_discount)}</div>
              </div>
            )}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
              <div className="text-xs font-medium text-emerald-600">Total Paid</div>
              <div className="text-base font-bold text-emerald-900 mt-0.5">{fmt(bill.total_paid)}</div>
            </div>
            <div className={`border rounded-xl p-3 ${bill.balance > 0 ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
              <div className={`text-xs font-medium ${bill.balance > 0 ? "text-red-600" : "text-gray-500"}`}>Balance Due</div>
              <div className={`text-base font-bold mt-0.5 ${bill.balance > 0 ? "text-red-900" : "text-gray-700"}`}>{fmt(bill.balance)}</div>
            </div>
          </div>

          {/* Bills table */}
          {bill.bills.length > 0 && (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">Bills</h3>
                {can("finance.waiver.create") && (
                  <button onClick={() => setWaiverOpen(true)} className="flex items-center gap-1.5 h-7 px-3 text-xs font-medium bg-amber-100 text-amber-700 hover:bg-amber-200 rounded-lg transition-colors">
                    + Grant Waiver
                  </button>
                )}
              </div>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                    <th className="px-4 py-2.5">Fee Type</th>
                    <th className="px-4 py-2.5">Billed</th>
                    <th className="px-4 py-2.5">Discount</th>
                    <th className="px-4 py-2.5">Paid</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5">Due Date</th>
                  </tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {bill.bills.map((b) => (
                      <tr key={b.id}>
                        <td className="px-4 py-2.5 text-gray-800">{b.fee_type_name}</td>
                        <td className="px-4 py-2.5 font-medium text-gray-900">{fmt(b.amount_due)}</td>
                        <td className="px-4 py-2.5 text-amber-600">{b.discount_amount > 0 ? `- ${fmt(b.discount_amount)}` : "—"}</td>
                        <td className="px-4 py-2.5 text-emerald-700">{b.amount_paid > 0 ? fmt(b.amount_paid) : "—"}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            b.status === "paid"    ? "bg-emerald-100 text-emerald-700" :
                            b.status === "waived"  ? "bg-amber-100 text-amber-700" :
                            b.status === "partial" ? "bg-blue-100 text-blue-700" :
                            "bg-red-100 text-red-700"
                          }`}>{b.status}</span>
                        </td>
                        <td className="px-4 py-2.5 text-gray-500">{b.due_date || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Waivers */}
          {bill.waivers.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700">Waivers / Discounts</h3>
              <div className="bg-white rounded-xl border border-amber-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-amber-50 text-left text-xs font-medium text-amber-700 uppercase">
                    <th className="px-4 py-2.5">Type</th>
                    <th className="px-4 py-2.5">Discount</th>
                    <th className="px-4 py-2.5">Fee</th>
                    <th className="px-4 py-2.5">Reason</th>
                    <th className="px-4 py-2.5">Granted By</th>
                    <th className="px-4 py-2.5 w-8" />
                  </tr></thead>
                  <tbody className="divide-y divide-amber-100">
                    {bill.waivers.map((w: WaiverRecord) => (
                      <tr key={w.id}>
                        <td className="px-4 py-2.5 capitalize text-gray-700">{w.waiver_type.replace(/_/g, " ")}</td>
                        <td className="px-4 py-2.5 font-medium text-amber-700">{w.discount_percent}%</td>
                        <td className="px-4 py-2.5 text-gray-500">{w.fee_type_name ?? "All bills"}</td>
                        <td className="px-4 py-2.5 text-gray-500">{w.reason || "—"}</td>
                        <td className="px-4 py-2.5 text-gray-400">{w.approved_by_name ?? "—"}</td>
                        <td className="px-4 py-2.5">
                          {can("finance.waiver.create") && (
                            <button onClick={() => handleRemoveWaiver(w.id)} className="text-gray-300 hover:text-red-500 transition-colors">×</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Payments */}
          {bill.payments.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700">Payments</h3>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                    <th className="px-4 py-2.5">Date</th>
                    <th className="px-4 py-2.5">Amount</th>
                    <th className="px-4 py-2.5">Method</th>
                    <th className="px-4 py-2.5">Reference</th>
                  </tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {bill.payments.map((p) => (
                      <tr key={p.id}>
                        <td className="px-4 py-2.5 text-gray-600">{p.payment_date}</td>
                        <td className="px-4 py-2.5 font-medium text-emerald-700">{fmt(p.amount_paid)}</td>
                        <td className="px-4 py-2.5 capitalize text-gray-600">{p.method}</td>
                        <td className="px-4 py-2.5 text-gray-400">{p.reference || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {waiverOpen && bill && (
        <WaiverDialog
          bill={bill}
          studentId={bill.student_id}
          onSave={() => { setWaiverOpen(false); lookup(selected); }}
          onClose={() => setWaiverOpen(false)}
        />
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
  const [term, setTerm]         = useState("");
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
        term: term ? Number(term) : null,
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
            <Field label="Term (leave blank for all terms)">
              <select className={INPUT} value={term} onChange={(e) => setTerm(e.target.value)}>
                <option value="">All Terms</option>
                <option value="1">Term 1</option>
                <option value="2">Term 2</option>
                <option value="3">Term 3</option>
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

// ── Manage tab (period locking, carry-forward, late fees) ──────────────────

function ManageTab({ years }: { years: AcademicYear[] }) {
  const toast = useToast();
  const { can } = useAuthStore();

  // Locked periods
  const [locked, setLocked]           = useState<LockedPeriod[]>([]);
  const [lockYear, setLockYear]       = useState(years.find((y) => y.is_current)?.id?.toString() ?? "");
  const [lockTerm, setLockTerm]       = useState("");
  const [lockNote, setLockNote]       = useState("");
  const [locking, setLocking]         = useState(false);

  // Carry-forward
  const [cfFrom, setCfFrom]           = useState(years.find((y) => y.is_current)?.id?.toString() ?? "");
  const [cfTo, setCfTo]               = useState("");
  const [cfTerm, setCfTerm]           = useState("");
  const [carrying, setCarrying]       = useState(false);
  const [cfResult, setCfResult]       = useState<{ created: number; skipped: number } | null>(null);

  // Late fee rules
  const [rules, setRules]             = useState<LateFeeRule[]>([]);
  const [ruleForm, setRuleForm]       = useState({ days_after_due: "7", charge_type: "percent", charge_amount: "", max_charge: "" });
  const [addingRule, setAddingRule]   = useState(false);
  const [applying, setApplying]       = useState(false);
  const [applyResult, setApplyResult] = useState<string>("");

  useEffect(() => {
    getLockedPeriods().then(setLocked).catch(() => {});
    getLateFeeRules().then(setRules).catch(() => {});
  }, []);

  const handleLock = async () => {
    if (!lockYear) return;
    setLocking(true);
    try {
      await lockPeriod({ academic_year_id: Number(lockYear), term: lockTerm ? Number(lockTerm) : null, note: lockNote || undefined });
      toast.success("Period locked");
      setLockNote("");
      getLockedPeriods().then(setLocked);
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed to lock"); }
    finally { setLocking(false); }
  };

  const handleUnlock = async (id: number) => {
    if (!confirm("Unlock this period? Transactions will be allowed again.")) return;
    await unlockPeriod(id).catch(() => toast.error("Failed to unlock"));
    getLockedPeriods().then(setLocked);
    toast.success("Period unlocked");
  };

  const handleCarryForward = async () => {
    if (!cfFrom || !cfTo) { toast.error("Select both years"); return; }
    setCarrying(true); setCfResult(null);
    try {
      const r = await carryForward({ from_year_id: Number(cfFrom), to_year_id: Number(cfTo), term: cfTerm ? Number(cfTerm) : null });
      setCfResult(r);
      toast.success(`${r.created} balances carried forward`);
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed"); }
    finally { setCarrying(false); }
  };

  const handleAddRule = async () => {
    if (!ruleForm.charge_amount) { toast.error("Enter charge amount"); return; }
    setAddingRule(true);
    try {
      await createLateFeeRule({
        days_after_due: Number(ruleForm.days_after_due),
        charge_type:    ruleForm.charge_type,
        charge_amount:  Number(ruleForm.charge_amount),
        max_charge:     ruleForm.max_charge ? Number(ruleForm.max_charge) : null,
      });
      toast.success("Rule added");
      setRuleForm({ days_after_due: "7", charge_type: "percent", charge_amount: "", max_charge: "" });
      getLateFeeRules().then(setRules);
    } catch { toast.error("Failed to add rule"); }
    finally { setAddingRule(false); }
  };

  const handleApplyLateFees = async () => {
    if (!confirm("Apply late fees to all overdue bills now?")) return;
    setApplying(true); setApplyResult("");
    try {
      const r = await applyLateFees(undefined, false);
      setApplyResult(`${r.applied} late fee bill${r.applied !== 1 ? "s" : ""} created`);
      toast.success(applyResult);
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed"); }
    finally { setApplying(false); }
  };

  const canManage = can("finance.structure.manage");

  return (
    <div className="space-y-8">

      {/* ── Carry-Forward ───────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <ArrowRightLeft size={15} className="text-violet-600" />
          <h3 className="text-sm font-semibold text-gray-800">Carry-Forward Balances</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">Creates a "Balance B/F" bill in the next year for each student with an outstanding balance.</p>
        <div className="grid grid-cols-3 gap-3 mb-3">
          <Field label="From Year *">
            <select className={INPUT} value={cfFrom} onChange={(e) => setCfFrom(e.target.value)}>
              {years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </Field>
          <Field label="To Year *">
            <select className={INPUT} value={cfTo} onChange={(e) => setCfTo(e.target.value)}>
              <option value="">Select…</option>
              {years.filter((y) => String(y.id) !== cfFrom).map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </Field>
          <Field label="Term (optional)">
            <select className={INPUT} value={cfTerm} onChange={(e) => setCfTerm(e.target.value)}>
              <option value="">All terms</option>
              <option value="1">Term 1</option>
              <option value="2">Term 2</option>
              <option value="3">Term 3</option>
            </select>
          </Field>
        </div>
        {cfResult && (
          <div className="mb-3 grid grid-cols-2 gap-3">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
              <div className="text-xl font-bold text-emerald-700">{cfResult.created}</div>
              <div className="text-xs text-emerald-600">Balances carried forward</div>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
              <div className="text-xl font-bold text-gray-500">{cfResult.skipped}</div>
              <div className="text-xs text-gray-400">Already existed</div>
            </div>
          </div>
        )}
        {canManage && (
          <Button variant="primary" icon={<ArrowRightLeft size={13} />} onClick={handleCarryForward} disabled={carrying || !cfFrom || !cfTo}>
            {carrying ? "Processing…" : "Carry Forward Balances"}
          </Button>
        )}
      </section>

      {/* ── Locked Periods ──────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Lock size={15} className="text-red-500" />
          <h3 className="text-sm font-semibold text-gray-800">Locked Accounting Periods</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">Locked periods prevent new bills, payments, or changes. Use this after closing a term or year.</p>
        {canManage && (
          <div className="flex gap-2 items-end mb-4">
            <Field label="Year">
              <select className={INPUT} value={lockYear} onChange={(e) => setLockYear(e.target.value)}>
                {years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
              </select>
            </Field>
            <Field label="Term (lock whole year if blank)">
              <select className={INPUT} value={lockTerm} onChange={(e) => setLockTerm(e.target.value)}>
                <option value="">Entire Year</option>
                <option value="1">Term 1</option>
                <option value="2">Term 2</option>
                <option value="3">Term 3</option>
              </select>
            </Field>
            <Field label="Note">
              <input className={INPUT} value={lockNote} onChange={(e) => setLockNote(e.target.value)} placeholder="e.g. End of year audit" />
            </Field>
            <button onClick={handleLock} disabled={locking} className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-40 transition-colors whitespace-nowrap">
              <Lock size={13} /> {locking ? "Locking…" : "Lock Period"}
            </button>
          </div>
        )}
        {locked.length === 0 ? (
          <p className="text-xs text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded-xl">No locked periods</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                <th className="px-4 py-2.5">Year</th>
                <th className="px-4 py-2.5">Term</th>
                <th className="px-4 py-2.5">Locked By</th>
                <th className="px-4 py-2.5">Date</th>
                <th className="px-4 py-2.5">Note</th>
                <th className="px-4 py-2.5 w-8" />
              </tr></thead>
              <tbody className="divide-y divide-gray-100">
                {locked.map((lp) => (
                  <tr key={lp.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-800">{lp.year_label}</td>
                    <td className="px-4 py-2.5"><span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">{lp.term ? `Term ${lp.term}` : "Full Year"}</span></td>
                    <td className="px-4 py-2.5 text-gray-500">{lp.locked_by_name}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{lp.locked_at?.slice(0, 10)}</td>
                    <td className="px-4 py-2.5 text-gray-400">{lp.note || "—"}</td>
                    <td className="px-4 py-2.5">
                      {canManage && (
                        <button onClick={() => handleUnlock(lp.id)} className="text-gray-300 hover:text-emerald-600 transition-colors" title="Unlock">
                          <Unlock size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Late Fee Rules ───────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Clock size={15} className="text-amber-500" />
          <h3 className="text-sm font-semibold text-gray-800">Late Fee Rules</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">Automatically add penalty charges to overdue bills. Click "Apply Late Fees" to run them now.</p>
        {canManage && (
          <div className="flex gap-2 items-end mb-4">
            <Field label="After (days)">
              <input type="number" min="1" className={INPUT} style={{width:90}} value={ruleForm.days_after_due} onChange={(e) => setRuleForm((f) => ({ ...f, days_after_due: e.target.value }))} />
            </Field>
            <Field label="Type">
              <select className={INPUT} style={{width:120}} value={ruleForm.charge_type} onChange={(e) => setRuleForm((f) => ({ ...f, charge_type: e.target.value }))}>
                <option value="percent">% of balance</option>
                <option value="fixed">Fixed (TZS)</option>
              </select>
            </Field>
            <Field label="Amount">
              <input type="number" min="0" className={INPUT} style={{width:100}} value={ruleForm.charge_amount} onChange={(e) => setRuleForm((f) => ({ ...f, charge_amount: e.target.value }))} placeholder={ruleForm.charge_type === "percent" ? "e.g. 5" : "e.g. 5000"} />
            </Field>
            <Field label="Max Charge (TZS, optional)">
              <input type="number" min="0" className={INPUT} style={{width:130}} value={ruleForm.max_charge} onChange={(e) => setRuleForm((f) => ({ ...f, max_charge: e.target.value }))} placeholder="No cap" />
            </Field>
            <button onClick={handleAddRule} disabled={addingRule} className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-40 transition-colors">
              <Plus size={13} /> Add Rule
            </button>
          </div>
        )}
        {rules.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-3">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                <th className="px-4 py-2.5">After Due</th>
                <th className="px-4 py-2.5">Charge</th>
                <th className="px-4 py-2.5">Max</th>
                <th className="px-4 py-2.5 w-8" />
              </tr></thead>
              <tbody className="divide-y divide-gray-100">
                {rules.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2.5 text-gray-700">{r.days_after_due} days late</td>
                    <td className="px-4 py-2.5 font-medium text-amber-700">
                      {r.charge_type === "percent" ? `${r.charge_amount}% of outstanding` : fmt(r.charge_amount)}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400">{r.max_charge ? fmt(r.max_charge) : "No cap"}</td>
                    <td className="px-4 py-2.5">
                      {canManage && (
                        <button onClick={() => deleteLateFeeRule(r.id).then(() => getLateFeeRules().then(setRules))} className="text-gray-300 hover:text-red-500 transition-colors">
                          <Trash2 size={13} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {canManage && rules.length > 0 && (
          <div className="flex items-center gap-3">
            <Button variant="outline" icon={<Zap size={13} />} onClick={handleApplyLateFees} disabled={applying}>
              {applying ? "Applying…" : "Apply Late Fees Now"}
            </Button>
            {applyResult && <span className="text-xs text-emerald-600">{applyResult}</span>}
          </div>
        )}
      </section>
    </div>
  );
}

// ── Approvals tab (maker/checker) ───────────────────────────────────────────

function ApprovalsTab() {
  const toast = useToast();
  const { can } = useAuthStore();
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading]     = useState(true);
  const [noteMap, setNoteMap]     = useState<Record<number, string>>({});

  const load = () => {
    setLoading(true);
    getPendingApprovals().then(setApprovals).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const handle = async (id: number, action: "approve" | "reject") => {
    const note = noteMap[id] || undefined;
    try {
      if (action === "approve") await approveAction(id, note);
      else await rejectAction(id, note);
      toast.success(action === "approve" ? "Approved" : "Rejected");
      load();
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed"); }
  };

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">Pending requests that require a second person to approve (maker/checker). You cannot approve your own requests.</p>
      {loading
        ? <div className="h-24 bg-gray-100 rounded-xl animate-pulse" />
        : approvals.length === 0
        ? <EmptyState icon={CheckCircle} title="No pending approvals" description="All requests have been resolved." />
        : (
          <div className="space-y-3">
            {approvals.map((a) => (
              <div key={a.id} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-1 ${a.action_type === "waiver" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                      {a.action_type === "waiver" ? "Waiver Request" : "Payment Reversal"}
                    </span>
                    <p className="text-sm text-gray-800">{a.description}</p>
                    <p className="text-xs text-gray-400 mt-0.5">Requested by <strong>{a.requester_name}</strong> · {a.created_at?.slice(0, 10)}</p>
                  </div>
                  {can("finance.waiver.approve") && (
                    <div className="flex flex-col gap-2 min-w-[180px]">
                      <input
                        className="h-8 px-2 border border-gray-200 rounded text-xs"
                        placeholder="Note (optional)"
                        value={noteMap[a.id] ?? ""}
                        onChange={(e) => setNoteMap((m) => ({ ...m, [a.id]: e.target.value }))}
                      />
                      <div className="flex gap-1.5">
                        <button onClick={() => handle(a.id, "approve")} className="flex-1 flex items-center justify-center gap-1 h-7 text-xs font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors">
                          <CheckCircle size={11} /> Approve
                        </button>
                        <button onClick={() => handle(a.id, "reject")} className="flex-1 flex items-center justify-center gap-1 h-7 text-xs font-medium bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors">
                          <XCircle size={11} /> Reject
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      }
    </div>
  );
}

// ── Invoices tab ────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  draft:          "bg-gray-100 text-gray-600",
  approved:       "bg-blue-100 text-blue-700",
  partially_paid: "bg-amber-100 text-amber-700",
  paid:           "bg-emerald-100 text-emerald-700",
  voided:         "bg-red-100 text-red-600",
  cancelled:      "bg-gray-100 text-gray-500",
};

function CreateInvoiceDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const toast = useToast();
  const [student, setStudent]   = useState<SelectedStudent | null>(null);
  const [items, setItems]       = useState([{ description: "", amount: "", discount_amount: "0", quantity: "1" }]);
  const [notes, setNotes]       = useState("");
  const [saving, setSaving]     = useState(false);

  const setItem = (i: number, k: string, v: string) =>
    setItems((prev) => prev.map((it, idx) => idx === i ? { ...it, [k]: v } : it));

  const addItem  = () => setItems((p) => [...p, { description: "", amount: "", discount_amount: "0", quantity: "1" }]);
  const removeItem = (i: number) => setItems((p) => p.filter((_, idx) => idx !== i));

  const total = items.reduce((s, it) => {
    const amt  = parseFloat(it.amount) || 0;
    const disc = parseFloat(it.discount_amount) || 0;
    const qty  = parseInt(it.quantity) || 1;
    return s + (amt - disc) * qty;
  }, 0);

  const submit = async () => {
    if (!student) { toast.error("Select a student first"); return; }
    for (const it of items) {
      if (!it.description.trim() || !it.amount || parseFloat(it.amount) <= 0) {
        toast.error("Each line item needs a description and a positive amount"); return;
      }
    }
    setSaving(true);
    try {
      await createInvoice({
        student_id: student.id,
        notes: notes || undefined,
        items: items.map((it) => ({
          description:     it.description,
          amount:          parseFloat(it.amount),
          discount_amount: parseFloat(it.discount_amount) || 0,
          quantity:        parseInt(it.quantity) || 1,
        })),
      });
      toast.success("Invoice created");
      onSave();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Failed to create invoice");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[92vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Create Invoice</h2>
        <div className="space-y-3">
          <Field label="Student *">
            <StudentSearch value={student} onChange={setStudent} />
          </Field>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-medium text-gray-600">Line Items *</label>
              <button type="button" onClick={addItem} className="text-xs text-violet-600 hover:underline">+ Add item</button>
            </div>
            <div className="space-y-2">
              {items.map((it, i) => (
                <div key={i} className="grid grid-cols-[1fr_100px_80px_24px] gap-2 items-end">
                  <div>
                    {i === 0 && <div className="text-2xs text-gray-400 mb-0.5">Description</div>}
                    <input className={INPUT} value={it.description} placeholder="e.g. Tuition Fee Term 1"
                      onChange={(e) => setItem(i, "description", e.target.value)} />
                  </div>
                  <div>
                    {i === 0 && <div className="text-2xs text-gray-400 mb-0.5">Amount (TZS)</div>}
                    <input type="number" min="0" className={INPUT} value={it.amount} placeholder="0"
                      onChange={(e) => setItem(i, "amount", e.target.value)} />
                  </div>
                  <div>
                    {i === 0 && <div className="text-2xs text-gray-400 mb-0.5">Discount</div>}
                    <input type="number" min="0" className={INPUT} value={it.discount_amount} placeholder="0"
                      onChange={(e) => setItem(i, "discount_amount", e.target.value)} />
                  </div>
                  <button type="button" onClick={() => removeItem(i)}
                    className={`text-gray-300 hover:text-red-500 mt-auto mb-1.5 transition-colors ${items.length === 1 ? "invisible" : ""}`}>×</button>
                </div>
              ))}
            </div>
            <div className="text-right text-xs text-gray-500 mt-1.5">
              Total: <span className="font-semibold text-gray-800">{fmt(total)}</span>
            </div>
          </div>

          <Field label="Notes">
            <input className={INPUT} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional notes…" />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Create Invoice"}</Button>
        </div>
      </div>
    </div>
  );
}

function InvoicePayDialog({ invoice, onSave, onClose }: { invoice: Invoice; onSave: () => void; onClose: () => void }) {
  const toast = useToast();
  const net = invoice.total_amount - invoice.discount_amount - invoice.paid_amount;
  const [form, setForm] = useState({
    control_number: invoice.control_number ?? "",
    amount: net.toFixed(2),
    payment_date: new Date().toISOString().slice(0, 10),
    method: "Cash",
    reference_no: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.control_number.trim()) { toast.error("Enter the control number"); return; }
    if (!form.amount || parseFloat(form.amount) <= 0) { toast.error("Enter a valid amount"); return; }
    setSaving(true);
    try {
      const res = await payInvoice(invoice.id, {
        control_number: form.control_number.trim(),
        amount: parseFloat(form.amount),
        payment_date: form.payment_date,
        method: form.method,
        reference_no: form.reference_no || undefined,
        notes: form.notes || undefined,
      });
      toast.success(`Payment recorded — balance: ${fmt(res.remaining_balance)}`);
      onSave();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Payment failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Record Payment</h2>
        <p className="text-sm text-gray-500 mb-4">{invoice.invoice_no} · {invoice.student_name} · Remaining: <strong>{fmt(net)}</strong></p>
        <div className="space-y-3">
          <Field label="Control Number *">
            <input className={INPUT + " font-mono"} value={form.control_number}
              onChange={(e) => set("control_number", e.target.value)} placeholder="SCH-YYYY-…" />
          </Field>
          <Field label="Amount (TZS) *">
            <input type="number" min="1" className={INPUT} value={form.amount} onChange={(e) => set("amount", e.target.value)} />
          </Field>
          <Field label="Payment Date *">
            <input type="date" className={INPUT} value={form.payment_date} onChange={(e) => set("payment_date", e.target.value)} />
          </Field>
          <Field label="Method">
            <select className={INPUT} value={form.method} onChange={(e) => set("method", e.target.value)}>
              <option>Cash</option>
              <option>Mobile Money</option>
              <option>Bank Transfer</option>
              <option>Cheque</option>
            </select>
          </Field>
          <Field label="Reference No">
            <input className={INPUT} value={form.reference_no} onChange={(e) => set("reference_no", e.target.value)} placeholder="Transaction reference…" />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Processing…" : "Record Payment"}</Button>
        </div>
      </div>
    </div>
  );
}

function AuditModal({ invoice, onClose }: { invoice: Invoice; onClose: () => void }) {
  const [log, setLog] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getInvoiceAudit(invoice.id).then(setLog).catch(() => {}).finally(() => setLoading(false));
  }, [invoice.id]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-gray-900">Audit Trail — {invoice.invoice_no}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        {loading ? (
          <div className="h-24 bg-gray-50 rounded-xl animate-pulse" />
        ) : log.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No audit entries</p>
        ) : (
          <ol className="relative border-l border-gray-200 pl-5 space-y-4">
            {log.map((e) => (
              <li key={e.id} className="ml-1">
                <div className="absolute -left-1.5 w-3 h-3 bg-violet-500 rounded-full mt-1" />
                <p className="text-xs font-semibold text-violet-700 uppercase tracking-wide">{e.action.replace(/_/g, " ")}</p>
                <p className="text-sm text-gray-800">{e.detail || "—"}</p>
                <p className="text-2xs text-gray-400 mt-0.5">by <strong>{e.actor_name || "system"}</strong> · {e.created_at?.slice(0, 16).replace("T", " ")}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function InvoicesTab() {
  const { can, user } = useAuthStore();
  const toast         = useToast();
  const [invoices, setInvoices]   = useState<Invoice[]>([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [createOpen, setCreateOpen]     = useState(false);
  const [payDialog, setPayDialog]       = useState<Invoice | null>(null);
  const [auditInv, setAuditInv]         = useState<Invoice | null>(null);

  const load = () => {
    setLoading(true);
    getInvoices({ limit: 200 })
      .then(setInvoices).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const filtered = invoices.filter((inv) => {
    const q = search.toLowerCase();
    const matchSearch = !q || inv.student_name.toLowerCase().includes(q) ||
      inv.admission_no.toLowerCase().includes(q) ||
      inv.invoice_no.toLowerCase().includes(q);
    const matchStatus = !filterStatus || inv.status === filterStatus;
    return matchSearch && matchStatus;
  });

  const handleApprove = async (inv: Invoice) => {
    if (inv.created_by === user?.id) {
      toast.error("Maker/checker rule: you cannot approve your own invoice");
      return;
    }
    try {
      await approveInvoice(inv.id);
      toast.success("Invoice approved");
      load();
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed to approve"); }
  };

  const handleIssueCtrl = async (inv: Invoice) => {
    try {
      const res = await issueControlNumber(inv.id);
      if (res.already_issued) toast.info?.(`Control number already issued: ${res.control_number}`);
      else toast.success("Control number issued");
      load();
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed to issue control number"); }
  };

  const handleVoid = async (inv: Invoice) => {
    const reason = prompt("Reason for voiding this invoice (required):");
    if (!reason || reason.trim().length < 5) { toast.error("Please provide a reason (min 5 chars)"); return; }
    try {
      await voidInvoice(inv.id, reason.trim());
      toast.success("Invoice voided");
      load();
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Failed to void invoice"); }
  };

  const copyCtrl = (ctrl: string) => {
    navigator.clipboard.writeText(ctrl).then(() => toast.success("Copied!")).catch(() => {});
  };

  const canCreate  = can("finance.payment.record");
  const canApprove = can("finance.waiver.approve");
  const canVoid    = can("finance.payment.void");

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="relative max-w-xs flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, adm no, invoice no…"
              className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </div>
          <select className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="partially_paid">Partially Paid</option>
            <option value="paid">Paid</option>
            <option value="voided">Voided</option>
          </select>
        </div>
        {canCreate && (
          <Button variant="primary" icon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Create Invoice</Button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-right">Paid</th>
              <th className="px-4 py-3 text-right">Balance</th>
              <th className="px-4 py-3">Control #</th>
              <th className="px-4 py-3 w-40">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={8} />)
              : filtered.length === 0
              ? (
                <tr>
                  <td colSpan={8} className="py-16">
                    <EmptyState icon={FileText} title="No invoices found"
                      description={search || filterStatus ? "Try adjusting your filters." : "Create your first invoice to get started."} />
                  </td>
                </tr>
              )
              : filtered.map((inv) => {
                const balance = inv.total_amount - inv.discount_amount - inv.paid_amount;
                return (
                  <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5">
                      <p className="font-mono text-xs font-semibold text-gray-800">{inv.invoice_no}</p>
                      <p className="text-2xs text-gray-400">{inv.created_at?.slice(0, 10)}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-gray-900">{inv.student_name}</p>
                      <p className="text-2xs text-gray-400">{inv.admission_no}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[inv.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {inv.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{fmt(inv.total_amount)}</td>
                    <td className="px-4 py-2.5 text-right text-emerald-700">{fmt(inv.paid_amount)}</td>
                    <td className="px-4 py-2.5 text-right font-semibold text-red-600">
                      {balance > 0.01 ? fmt(balance) : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2.5">
                      {inv.control_number ? (
                        <div className="flex items-center gap-1">
                          <span className="font-mono text-2xs text-violet-700 bg-violet-50 px-1.5 py-0.5 rounded truncate max-w-[130px]" title={inv.control_number}>
                            {inv.control_number}
                          </span>
                          <button onClick={() => copyCtrl(inv.control_number!)} className="text-gray-300 hover:text-violet-600 transition-colors flex-shrink-0">
                            <Copy size={11} />
                          </button>
                        </div>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1 flex-wrap">
                        {inv.status === "draft" && canApprove && inv.created_by !== user?.id && (
                          <button onClick={() => handleApprove(inv)}
                            className="flex items-center gap-0.5 h-6 px-2 text-2xs font-medium bg-blue-100 text-blue-700 hover:bg-blue-200 rounded transition-colors">
                            <ShieldCheck size={10} /> Approve
                          </button>
                        )}
                        {inv.status === "approved" && !inv.control_number && can("finance.payment.record") && (
                          <button onClick={() => handleIssueCtrl(inv)}
                            className="h-6 px-2 text-2xs font-medium bg-violet-100 text-violet-700 hover:bg-violet-200 rounded transition-colors">
                            Issue Ctrl #
                          </button>
                        )}
                        {(inv.status === "approved" || inv.status === "partially_paid") && inv.control_number && can("finance.payment.record") && (
                          <button onClick={() => setPayDialog(inv)}
                            className="h-6 px-2 text-2xs font-medium bg-emerald-100 text-emerald-700 hover:bg-emerald-200 rounded transition-colors">
                            Pay
                          </button>
                        )}
                        {inv.status !== "paid" && inv.status !== "voided" && inv.status !== "cancelled" && canVoid && (
                          <button onClick={() => handleVoid(inv)}
                            className="h-6 px-2 text-2xs font-medium bg-red-50 text-red-500 hover:bg-red-100 rounded transition-colors">
                            Void
                          </button>
                        )}
                        <button onClick={() => setAuditInv(inv)}
                          className="h-6 px-2 text-2xs font-medium text-gray-400 hover:text-gray-600 border border-gray-200 rounded transition-colors">
                          Log
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>

      {createOpen && (
        <CreateInvoiceDialog onSave={() => { setCreateOpen(false); load(); }} onClose={() => setCreateOpen(false)} />
      )}
      {payDialog && (
        <InvoicePayDialog invoice={payDialog} onSave={() => { setPayDialog(null); load(); }} onClose={() => setPayDialog(null)} />
      )}
      {auditInv && (
        <AuditModal invoice={auditInv} onClose={() => setAuditInv(null)} />
      )}
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
    else if (tab === "fees" || tab === "manage") loadFees();
    else setLoading(false);
  }, [tab, loadPayments, loadFees]);

  const TABS = [
    { key: "payments" as Tab,     label: "Payments" },
    { key: "fees" as Tab,         label: "Fee Structures" },
    { key: "student-bill" as Tab, label: "Student Bill" },
    { key: "outstanding" as Tab,  label: "Outstanding Debts" },
    { key: "invoices" as Tab,     label: "Invoices",         perm: "finance.view" },
    { key: "manage" as Tab,       label: "Period & Rules",   perm: "finance.structure.view" },
    { key: "approvals" as Tab,    label: "Approvals",        perm: "finance.view" },
  ].filter((t) => !t.perm || can(t.perm as string));

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
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Term</th>
              <th className="px-4 py-3">Academic Year</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Due Date</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
                : feeStructures.length === 0
                ? <tr><td colSpan={7} className="py-16"><EmptyState icon={DollarSign} title="No fee structures" description="Add fee structures to bill students." /></td></tr>
                : feeStructures.map((fs) => (
                  <tr key={fs.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{fs.fee_type_name}</td>
                    <td className="px-4 py-3">
                      {fs.student_name
                        ? <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">{fs.student_name} <span className="opacity-60">({fs.student_admission_no})</span></span>
                        : fs.class_name
                        ? <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded text-xs font-medium">{fs.class_name}</span>
                        : <span className="text-gray-400 text-xs">All students</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fs.student_type ?? "All"}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fs.term ? `Term ${fs.term}` : "All"}</td>
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
      {tab === "invoices"     && <InvoicesTab />}
      {tab === "manage"       && <ManageTab years={years} />}
      {tab === "approvals"    && <ApprovalsTab />}

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
