import { useState, useEffect, useRef } from "react";
import {
  Users, PlayCircle, CheckCircle, FileText, ChevronRight,
  Edit2, X, Printer, AlertCircle, Plus,
} from "lucide-react";
import {
  getPayrollStaff, setSalaryConfig, getPayrollRuns, createPayrollRun,
  computeRun, finalizeRun, approveRun, getRunItems,
  type StaffSalary, type PayrollRun, type PayrollItem, type SalaryConfigPayload,
} from "@/api/payroll";
import { useAuthStore } from "@/stores/authStore";

// ─── helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number | null | undefined) =>
  n == null ? "—" : `TZS ${n.toLocaleString("en-TZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const STATUS_COLOR: Record<string, string> = {
  draft:     "bg-yellow-100 text-yellow-800",
  finalized: "bg-blue-100 text-blue-800",
  approved:  "bg-green-100 text-green-800",
};

const MONTHS = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// ─── Salary Config Dialog ─────────────────────────────────────────────────────

function SalaryDialog({
  staff,
  onClose,
  onSave,
}: {
  staff: StaffSalary;
  onClose: () => void;
  onSave: () => void;
}) {
  const [form, setForm] = useState<SalaryConfigPayload>({
    basic_salary:    staff.basic_salary    ?? 0,
    housing_allow:   staff.housing_allow   ?? 0,
    transport_allow: staff.transport_allow ?? 0,
    other_allow:     staff.other_allow     ?? 0,
    loan_deduction:  staff.loan_deduction  ?? 0,
    loan_board:      Boolean(staff.loan_board),
    notes:           staff.notes           ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const gross = form.basic_salary + form.housing_allow + form.transport_allow + form.other_allow;

  const set = (k: keyof SalaryConfigPayload) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const val = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : Number(e.target.value);
    setForm((f) => ({ ...f, [k]: val }));
  };

  const save = async () => {
    setSaving(true);
    setErr("");
    try {
      await setSalaryConfig(staff.id, form);
      onSave();
      onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Salary Config — {staff.first_name} {staff.last_name}
          </h2>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          {(
            [
              ["basic_salary",    "Basic Salary"],
              ["housing_allow",   "Housing Allowance"],
              ["transport_allow", "Transport Allowance"],
              ["other_allow",     "Other Allowances"],
              ["loan_deduction",  "Loan Deduction"],
            ] as [keyof SalaryConfigPayload, string][]
          ).map(([key, label]) => (
            <div key={key}>
              <label className="text-xs text-gray-500 font-medium">{label} (TZS)</label>
              <input
                type="number"
                min={0}
                step={1000}
                value={form[key] as number}
                onChange={set(key)}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          ))}

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="loan_board"
              checked={form.loan_board}
              onChange={set("loan_board")}
              className="w-4 h-4"
            />
            <label htmlFor="loan_board" className="text-sm text-gray-700">
              Loan Board deduction (15%)
            </label>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-xs text-gray-500 font-medium">Notes</label>
          <textarea
            rows={2}
            value={form.notes}
            onChange={set("notes")}
            className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
          />
        </div>

        <div className="bg-blue-50 rounded-lg p-3 mb-4 text-sm">
          <span className="text-gray-600">Gross Pay:</span>{" "}
          <span className="font-semibold text-blue-700">{fmt(gross)}</span>
        </div>

        {err && <p className="text-red-600 text-sm mb-3">{err}</p>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Payslip Print View ───────────────────────────────────────────────────────

function PayslipModal({
  item,
  runLabel,
  onClose,
}: {
  item: PayrollItem;
  runLabel: string;
  onClose: () => void;
}) {
  const printRef = useRef<HTMLDivElement>(null);

  const print = () => {
    const content = printRef.current?.innerHTML ?? "";
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`<html><head><title>Payslip</title>
      <style>
        body { font-family: Arial, sans-serif; font-size: 13px; margin: 32px; color: #111; }
        h1 { font-size: 18px; margin-bottom: 4px; }
        .school { font-size: 14px; color: #555; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th { background: #f3f4f6; text-align: left; padding: 6px 10px; font-size: 12px; }
        td { padding: 5px 10px; border-bottom: 1px solid #e5e7eb; }
        .total td { font-weight: 700; background: #f9fafb; }
        .net td { font-weight: 700; font-size: 15px; color: #1d4ed8; background: #eff6ff; }
        .sig { margin-top: 48px; display: flex; justify-content: space-between; }
        .sig-line { border-top: 1px solid #111; width: 180px; text-align: center; padding-top: 4px; font-size: 11px; }
      </style></head><body>${content}</body></html>`);
    win.document.close();
    win.print();
  };

  const row = (label: string, val: number, cls = "") => (
    <tr className={cls}>
      <td className="text-gray-600">{label}</td>
      <td className="text-right font-mono">{fmt(val)}</td>
    </tr>
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold text-gray-900">Payslip — {runLabel}</h2>
          <div className="flex gap-2">
            <button
              onClick={print}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              <Printer size={14} /> Print
            </button>
            <button onClick={onClose}><X size={20} /></button>
          </div>
        </div>

        <div ref={printRef} className="p-6">
          <h1 className="text-xl font-bold text-gray-900">PAYSLIP</h1>
          <p className="text-gray-500 text-sm mb-4">{runLabel}</p>

          <div className="grid grid-cols-2 gap-1 text-sm mb-4">
            <div><span className="text-gray-500">Name:</span> <strong>{item.first_name} {item.last_name}</strong></div>
            <div><span className="text-gray-500">Employee No:</span> <strong>{item.employee_no}</strong></div>
            <div><span className="text-gray-500">Designation:</span> {item.subject_specialization || "—"}</div>
          </div>

          <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
            <thead>
              <tr className="bg-gray-50">
                <th className="text-left p-2 pl-3 text-gray-600">Description</th>
                <th className="text-right p-2 pr-3 text-gray-600">Amount (TZS)</th>
              </tr>
            </thead>
            <tbody>
              <tr className="bg-green-50">
                <td colSpan={2} className="p-2 pl-3 text-xs font-semibold text-green-700 uppercase tracking-wide">
                  Earnings
                </td>
              </tr>
              {row("Basic Salary", item.basic_salary)}
              {item.housing_allow > 0 && row("Housing Allowance", item.housing_allow)}
              {item.transport_allow > 0 && row("Transport Allowance", item.transport_allow)}
              {item.other_allow > 0 && row("Other Allowances", item.other_allow)}
              <tr className="bg-green-50 font-semibold">
                <td className="p-2 pl-3">Gross Pay</td>
                <td className="text-right font-mono p-2 pr-3">{fmt(item.gross_pay)}</td>
              </tr>

              <tr className="bg-red-50">
                <td colSpan={2} className="p-2 pl-3 text-xs font-semibold text-red-700 uppercase tracking-wide">
                  Deductions
                </td>
              </tr>
              {row("NSSF (Employee 10%)", item.nssf_employee)}
              {row("PAYE Tax", item.paye)}
              {item.loan_deduction > 0 && row("Loan Deduction", item.loan_deduction)}
              {item.loan_board > 0 && row("Loan Board (HESLB 15%)", item.loan_board)}
              <tr className="bg-red-50 font-semibold">
                <td className="p-2 pl-3">Total Deductions</td>
                <td className="text-right font-mono p-2 pr-3">{fmt(item.total_deductions)}</td>
              </tr>

              <tr className="bg-blue-50">
                <td className="p-2 pl-3 font-bold text-blue-800 text-base">NET PAY</td>
                <td className="text-right font-mono p-2 pr-3 font-bold text-blue-800 text-base">
                  {fmt(item.net_pay)}
                </td>
              </tr>
            </tbody>
          </table>

          <div className="sig mt-12 flex justify-between">
            <div className="sig-line">
              <div className="h-10" />
              <div>Employee Signature</div>
            </div>
            <div className="sig-line">
              <div className="h-10" />
              <div>Authorized Signature</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Run Detail Modal ─────────────────────────────────────────────────────────

function RunDetailModal({
  run,
  onClose,
  onRefresh,
}: {
  run: PayrollRun;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const { can } = useAuthStore();
  const [items, setItems] = useState<PayrollItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [err, setErr] = useState("");
  const [printItem, setPrintItem] = useState<PayrollItem | null>(null);

  const load = () => {
    setLoading(true);
    getRunItems(run.id)
      .then((d) => setItems(d.items))
      .finally(() => setLoading(false));
  };

  useEffect(load, [run.id]);

  const action = async (fn: () => Promise<any>, label: string) => {
    setWorking(true);
    setErr("");
    try {
      await fn();
      onRefresh();
      load();
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? `${label} failed`);
    } finally {
      setWorking(false);
    }
  };

  const totalGross = items.reduce((s, i) => s + i.gross_pay, 0);
  const totalNssf  = items.reduce((s, i) => s + i.nssf_employee, 0);
  const totalPaye  = items.reduce((s, i) => s + i.paye, 0);
  const totalNet   = items.reduce((s, i) => s + i.net_pay, 0);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        {/* header */}
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">{run.label}</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLOR[run.status]}`}>
              {run.status}
            </span>
          </div>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        {/* actions */}
        {can("payroll.manage") && (
          <div className="flex gap-2 px-4 py-3 border-b bg-gray-50 shrink-0 flex-wrap">
            {run.status === "draft" && (
              <button
                onClick={() => action(() => computeRun(run.id), "Compute")}
                disabled={working}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <PlayCircle size={14} />
                {working ? "Working…" : items.length ? "Recompute" : "Compute Payroll"}
              </button>
            )}
            {run.status === "draft" && items.length > 0 && (
              <button
                onClick={() => action(() => finalizeRun(run.id), "Finalize")}
                disabled={working}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                <CheckCircle size={14} /> Finalize
              </button>
            )}
            {run.status === "finalized" && can("payroll.approve") && (
              <button
                onClick={() => action(() => approveRun(run.id), "Approve")}
                disabled={working}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCircle size={14} /> Approve & Post to Ledger
              </button>
            )}
            {err && <p className="text-red-600 text-sm self-center">{err}</p>}
          </div>
        )}

        {/* summary */}
        {items.length > 0 && (
          <div className="grid grid-cols-4 gap-px bg-gray-200 border-b shrink-0">
            {[
              ["Employees", items.length, false],
              ["Gross Pay", totalGross, true],
              ["Deductions", totalNssf + totalPaye, true],
              ["Net Pay", totalNet, true],
            ].map(([label, val, money]) => (
              <div key={label as string} className="bg-white p-3 text-center">
                <div className="text-xs text-gray-500">{label}</div>
                <div className="font-semibold text-gray-900 text-sm">
                  {money ? fmt(val as number) : val}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* table */}
        <div className="overflow-auto flex-1">
          {loading ? (
            <div className="p-8 text-center text-gray-400">Loading…</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No payslips yet. Click "Compute Payroll" to generate.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50">
                <tr>
                  <th className="text-left p-2 pl-4 text-gray-600 font-medium">Employee</th>
                  <th className="text-right p-2 text-gray-600 font-medium">Basic</th>
                  <th className="text-right p-2 text-gray-600 font-medium">Gross</th>
                  <th className="text-right p-2 text-gray-600 font-medium">NSSF</th>
                  <th className="text-right p-2 text-gray-600 font-medium">PAYE</th>
                  <th className="text-right p-2 text-gray-600 font-medium">Other Ded.</th>
                  <th className="text-right p-2 pr-4 text-gray-600 font-medium">Net Pay</th>
                  <th className="p-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="p-2 pl-4">
                      <div className="font-medium text-gray-900">
                        {item.first_name} {item.last_name}
                      </div>
                      <div className="text-xs text-gray-400">{item.employee_no}</div>
                    </td>
                    <td className="text-right p-2 font-mono text-gray-700">
                      {fmt(item.basic_salary)}
                    </td>
                    <td className="text-right p-2 font-mono text-gray-700">
                      {fmt(item.gross_pay)}
                    </td>
                    <td className="text-right p-2 font-mono text-red-600">
                      {fmt(item.nssf_employee)}
                    </td>
                    <td className="text-right p-2 font-mono text-red-600">
                      {fmt(item.paye)}
                    </td>
                    <td className="text-right p-2 font-mono text-red-600">
                      {fmt(item.loan_deduction + item.loan_board)}
                    </td>
                    <td className="text-right p-2 pr-4 font-mono font-semibold text-blue-700">
                      {fmt(item.net_pay)}
                    </td>
                    <td className="p-2">
                      <button
                        onClick={() => setPrintItem(item)}
                        className="text-gray-400 hover:text-gray-700"
                        title="View payslip"
                      >
                        <FileText size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {printItem && (
        <PayslipModal
          item={printItem}
          runLabel={run.label}
          onClose={() => setPrintItem(null)}
        />
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PayrollPage() {
  const { can } = useAuthStore();
  const [tab, setTab] = useState<"runs" | "staff">("runs");

  // runs tab
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<PayrollRun | null>(null);
  const [showCreateRun, setShowCreateRun] = useState(false);
  const [newMonth, setNewMonth] = useState(new Date().getMonth() + 1);
  const [newYear, setNewYear]   = useState(new Date().getFullYear());
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState("");

  // staff tab
  const [staff, setStaff] = useState<StaffSalary[]>([]);
  const [staffSearch, setStaffSearch] = useState("");
  const [staffLoading, setStaffLoading] = useState(false);
  const [editStaff, setEditStaff] = useState<StaffSalary | null>(null);

  const loadRuns = () => {
    setRunsLoading(true);
    getPayrollRuns().then(setRuns).finally(() => setRunsLoading(false));
  };

  const loadStaff = () => {
    setStaffLoading(true);
    getPayrollStaff(staffSearch).then(setStaff).finally(() => setStaffLoading(false));
  };

  useEffect(() => { loadRuns(); }, []);
  useEffect(() => { if (tab === "staff") loadStaff(); }, [tab, staffSearch]);

  const handleCreateRun = async () => {
    setCreating(true);
    setCreateErr("");
    try {
      await createPayrollRun(newMonth, newYear);
      setShowCreateRun(false);
      loadRuns();
    } catch (e: any) {
      setCreateErr(e?.response?.data?.detail ?? "Failed to create run");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* page header */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Payroll</h1>
          <p className="text-sm text-gray-500">Salary management and monthly payroll processing</p>
        </div>
      </div>

      {/* tabs */}
      <div className="bg-white border-b px-6 flex gap-1">
        {(["runs", "staff"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
              tab === t
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {t === "runs" ? "Payroll Runs" : "Staff Salaries"}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-6">
        {/* ── Runs tab ── */}
        {tab === "runs" && (
          <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-gray-600">Monthly payroll runs</h2>
              {can("payroll.manage") && (
                <button
                  onClick={() => setShowCreateRun(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Plus size={14} /> New Run
                </button>
              )}
            </div>

            {/* create run inline form */}
            {showCreateRun && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 flex items-end gap-3 flex-wrap">
                <div>
                  <label className="text-xs text-gray-600 font-medium">Month</label>
                  <select
                    value={newMonth}
                    onChange={(e) => setNewMonth(Number(e.target.value))}
                    className="mt-1 block border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {MONTHS.slice(1).map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-600 font-medium">Year</label>
                  <input
                    type="number"
                    value={newYear}
                    onChange={(e) => setNewYear(Number(e.target.value))}
                    className="mt-1 block w-28 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <button
                  onClick={handleCreateRun}
                  disabled={creating}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Create"}
                </button>
                <button
                  onClick={() => setShowCreateRun(false)}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-white"
                >
                  Cancel
                </button>
                {createErr && (
                  <p className="text-red-600 text-sm flex items-center gap-1">
                    <AlertCircle size={14} /> {createErr}
                  </p>
                )}
              </div>
            )}

            {runsLoading ? (
              <div className="text-center text-gray-400 py-12">Loading…</div>
            ) : runs.length === 0 ? (
              <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-dashed">
                No payroll runs yet. Create the first one above.
              </div>
            ) : (
              <div className="bg-white rounded-xl border divide-y">
                {runs.map((run) => (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRun(run)}
                    className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 text-left transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="font-medium text-gray-900">{run.label}</div>
                        <div className="text-xs text-gray-400">
                          {run.employee_count} employee{run.employee_count !== 1 ? "s" : ""}
                          {run.total_net != null && ` · Net: ${fmt(run.total_net)}`}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLOR[run.status]}`}>
                        {run.status}
                      </span>
                      <ChevronRight size={16} className="text-gray-400" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Staff tab ── */}
        {tab === "staff" && (
          <div className="max-w-5xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-gray-600">
                Staff salary configuration
              </h2>
              <input
                type="text"
                placeholder="Search staff…"
                value={staffSearch}
                onChange={(e) => setStaffSearch(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none w-56"
              />
            </div>

            {staffLoading ? (
              <div className="text-center text-gray-400 py-12">Loading…</div>
            ) : (
              <div className="bg-white rounded-xl border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left p-3 pl-4 text-gray-600 font-medium">Employee</th>
                      <th className="text-right p-3 text-gray-600 font-medium">Basic</th>
                      <th className="text-right p-3 text-gray-600 font-medium">Allowances</th>
                      <th className="text-right p-3 text-gray-600 font-medium">Gross</th>
                      <th className="text-right p-3 text-gray-600 font-medium">Deductions</th>
                      {can("payroll.manage") && <th className="p-3 w-10" />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {staff.map((s) => {
                      const gross = (s.basic_salary ?? 0) + (s.housing_allow ?? 0)
                        + (s.transport_allow ?? 0) + (s.other_allow ?? 0);
                      const ded = (s.loan_deduction ?? 0) + (s.loan_board ? gross * 0.15 : 0);
                      const configured = s.basic_salary != null;
                      return (
                        <tr key={s.id} className="hover:bg-gray-50">
                          <td className="p-3 pl-4">
                            <div className="font-medium text-gray-900">
                              {s.first_name} {s.last_name}
                            </div>
                            <div className="text-xs text-gray-400">{s.employee_no}</div>
                          </td>
                          <td className="text-right p-3 font-mono text-gray-700">
                            {configured ? fmt(s.basic_salary) : <span className="text-gray-300 text-xs">not set</span>}
                          </td>
                          <td className="text-right p-3 font-mono text-gray-700">
                            {configured
                              ? fmt((s.housing_allow ?? 0) + (s.transport_allow ?? 0) + (s.other_allow ?? 0))
                              : "—"}
                          </td>
                          <td className="text-right p-3 font-mono font-medium text-gray-900">
                            {configured ? fmt(gross) : "—"}
                          </td>
                          <td className="text-right p-3 font-mono text-red-600">
                            {configured ? fmt(ded) : "—"}
                          </td>
                          {can("payroll.manage") && (
                            <td className="p-3">
                              <button
                                onClick={() => setEditStaff(s)}
                                className="text-blue-500 hover:text-blue-700"
                                title="Configure salary"
                              >
                                <Edit2 size={14} />
                              </button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                    {staff.length === 0 && (
                      <tr>
                        <td colSpan={6} className="text-center text-gray-400 py-8">
                          No active staff found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* modals */}
      {selectedRun && (
        <RunDetailModal
          run={selectedRun}
          onClose={() => setSelectedRun(null)}
          onRefresh={loadRuns}
        />
      )}
      {editStaff && (
        <SalaryDialog
          staff={editStaff}
          onClose={() => setEditStaff(null)}
          onSave={loadStaff}
        />
      )}
    </div>
  );
}
