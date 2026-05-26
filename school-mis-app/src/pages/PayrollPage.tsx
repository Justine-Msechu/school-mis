import { useState, useEffect, useRef } from "react";
import {
  Users, PlayCircle, CheckCircle, FileText, ChevronRight,
  Edit2, X, Printer, AlertCircle, Plus, Trash2, RotateCcw,
  Download, History, Calendar,
} from "lucide-react";
import {
  getPayrollStaff, setSalaryConfig, getPayrollRuns, createPayrollRun,
  deletePayrollRun, reopenRun, computeRun, finalizeRun, approveRun,
  getRunItems, updateProrate, getYTD, getStaffHistory,
  type StaffSalary, type PayrollRun, type PayrollItem,
  type SalaryConfigPayload, type YTDRow, type HistoryItem,
} from "@/api/payroll";
import { useAuthStore } from "@/stores/authStore";

// ─── helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number | null | undefined) =>
  n == null
    ? "—"
    : `TZS ${n.toLocaleString("en-TZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const fmtN = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-TZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const STATUS_COLOR: Record<string, string> = {
  draft:     "bg-yellow-100 text-yellow-800",
  finalized: "bg-blue-100 text-blue-800",
  approved:  "bg-green-100 text-green-800",
};

const MONTHS = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// ─── CSV export helpers ───────────────────────────────────────────────────────

function downloadCSV(filename: string, rows: string[][]): void {
  const content = rows
    .map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportRegisterCSV(items: PayrollItem[], run: PayrollRun) {
  const header = [
    "No", "Employee No", "Name", "Basic Salary", "Housing Allow",
    "Transport Allow", "Other Allow", "Gross Pay", "NSSF (Employee)",
    "NSSF (Employer)", "PAYE", "Loan Deduction", "Loan Board (HESLB)",
    "Total Deductions", "Net Pay", "Pro-rate %",
  ];
  const rows = items.map((it, i) => [
    String(i + 1),
    it.employee_no,
    `${it.first_name} ${it.last_name}`,
    String(it.basic_salary),
    String(it.housing_allow),
    String(it.transport_allow),
    String(it.other_allow),
    String(it.gross_pay),
    String(it.nssf_employee),
    String(it.nssf_employer),
    String(it.paye),
    String(it.loan_deduction),
    String(it.loan_board),
    String(it.total_deductions),
    String(it.net_pay),
    String(it.prorate_pct),
  ]);
  // totals row
  const sum = (key: keyof PayrollItem) =>
    String(items.reduce((s, it) => s + Number(it[key] ?? 0), 0).toFixed(2));
  rows.push([
    "", "", "TOTAL", sum("basic_salary"), sum("housing_allow"),
    sum("transport_allow"), sum("other_allow"), sum("gross_pay"),
    sum("nssf_employee"), sum("nssf_employer"), sum("paye"),
    sum("loan_deduction"), sum("loan_board"), sum("total_deductions"), sum("net_pay"), "",
  ]);
  downloadCSV(`Payroll_Register_${run.label.replace(/ /g, "_")}.csv`, [header, ...rows]);
}

function exportBankListCSV(items: PayrollItem[], run: PayrollRun) {
  const header = ["No", "Employee No", "Employee Name", "Net Pay (TZS)"];
  const rows = items.map((it, i) => [
    String(i + 1), it.employee_no,
    `${it.first_name} ${it.last_name}`, String(it.net_pay),
  ]);
  const total = items.reduce((s, it) => s + it.net_pay, 0);
  rows.push(["", "", "TOTAL", String(total.toFixed(2))]);
  downloadCSV(`Bank_Payment_List_${run.label.replace(/ /g, "_")}.csv`, [header, ...rows]);
}

function exportNSSFCSV(items: PayrollItem[], run: PayrollRun) {
  const header = [
    "No", "Employee No", "Name", "Gross Pay",
    "NSSF Employee (10%)", "NSSF Employer (10%)", "Total NSSF",
  ];
  const rows = items.map((it, i) => [
    String(i + 1), it.employee_no,
    `${it.first_name} ${it.last_name}`,
    String(it.gross_pay), String(it.nssf_employee),
    String(it.nssf_employer),
    String((it.nssf_employee + it.nssf_employer).toFixed(2)),
  ]);
  const totals = items.reduce(
    (acc, it) => ({
      gross: acc.gross + it.gross_pay,
      emp: acc.emp + it.nssf_employee,
      er: acc.er + it.nssf_employer,
    }),
    { gross: 0, emp: 0, er: 0 },
  );
  rows.push([
    "", "", "TOTAL",
    String(totals.gross.toFixed(2)),
    String(totals.emp.toFixed(2)),
    String(totals.er.toFixed(2)),
    String((totals.emp + totals.er).toFixed(2)),
  ]);
  downloadCSV(`NSSF_Return_${run.label.replace(/ /g, "_")}.csv`, [header, ...rows]);
}

function exportPAYECSV(items: PayrollItem[], run: PayrollRun) {
  const header = ["No", "Employee No", "Name", "Gross Pay", "NSSF Deducted", "Taxable Income", "PAYE"];
  const rows = items.map((it, i) => [
    String(i + 1), it.employee_no,
    `${it.first_name} ${it.last_name}`,
    String(it.gross_pay), String(it.nssf_employee),
    String((it.gross_pay - it.nssf_employee).toFixed(2)),
    String(it.paye),
  ]);
  const total = items.reduce((s, it) => s + it.paye, 0);
  rows.push(["", "", "TOTAL", "", "", "", String(total.toFixed(2))]);
  downloadCSV(`PAYE_Return_${run.label.replace(/ /g, "_")}.csv`, [header, ...rows]);
}

// ─── Salary Config Dialog ─────────────────────────────────────────────────────

function SalaryDialog({ staff, onClose, onSave }: {
  staff: StaffSalary; onClose: () => void; onSave: () => void;
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

  const setF =
    (k: keyof SalaryConfigPayload) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const val = e.target.type === "checkbox"
        ? (e.target as HTMLInputElement).checked
        : Number(e.target.value);
      setForm((f) => ({ ...f, [k]: val }));
    };

  const save = async () => {
    setSaving(true); setErr("");
    try { await setSalaryConfig(staff.id, form); onSave(); onClose(); }
    catch (e: any) { setErr(e?.response?.data?.detail ?? "Failed to save"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Salary — {staff.first_name} {staff.last_name}
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
                type="number" min={0} step={1000}
                value={form[key] as number}
                onChange={setF(key)}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          ))}
          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox" id="loan_board" checked={form.loan_board}
              onChange={setF("loan_board")} className="w-4 h-4"
            />
            <label htmlFor="loan_board" className="text-sm text-gray-700">
              Loan Board (HESLB 15%)
            </label>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-xs text-gray-500 font-medium">Notes</label>
          <textarea
            rows={2} value={form.notes} onChange={setF("notes")}
            className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
          />
        </div>

        <div className="bg-blue-50 rounded-lg p-3 mb-4 text-sm">
          <span className="text-gray-600">Gross Pay (full month):</span>{" "}
          <span className="font-semibold text-blue-700">{fmt(gross)}</span>
        </div>

        {err && <p className="text-red-600 text-sm mb-3">{err}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Cancel</button>
          <button onClick={save} disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Employee History Modal ───────────────────────────────────────────────────

function HistoryModal({ staff, onClose }: { staff: StaffSalary; onClose: () => void }) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStaffHistory(staff.id).then(setHistory).finally(() => setLoading(false));
  }, [staff.id]);

  const ytdGross = history.filter((h) => h.run_status !== "draft")
    .reduce((s, h) => s + h.gross_pay, 0);
  const ytdNet = history.filter((h) => h.run_status !== "draft")
    .reduce((s, h) => s + h.net_pay, 0);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div>
            <h2 className="font-semibold text-gray-900">
              Payroll History — {staff.first_name} {staff.last_name}
            </h2>
            <p className="text-xs text-gray-400">{staff.employee_no}</p>
          </div>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        {history.length > 0 && (
          <div className="grid grid-cols-3 gap-px bg-gray-200 border-b shrink-0">
            {[
              ["Payroll Runs", history.length],
              ["YTD Gross", fmt(ytdGross)],
              ["YTD Net Pay", fmt(ytdNet)],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-white p-3 text-center">
                <div className="text-xs text-gray-500">{label}</div>
                <div className="font-semibold text-gray-900 text-sm">{val}</div>
              </div>
            ))}
          </div>
        )}

        <div className="overflow-auto flex-1">
          {loading ? (
            <div className="p-8 text-center text-gray-400">Loading…</div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center text-gray-400">No payroll history found.</div>
          ) : (
            <div className="table-scroll"><table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 pl-4 font-medium text-gray-600">Period</th>
                  <th className="text-right p-3 font-medium text-gray-600">Gross</th>
                  <th className="text-right p-3 font-medium text-gray-600">NSSF</th>
                  <th className="text-right p-3 font-medium text-gray-600">PAYE</th>
                  <th className="text-right p-3 pr-4 font-medium text-gray-600">Net Pay</th>
                  <th className="p-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((h) => (
                  <tr key={h.id} className="hover:bg-gray-50">
                    <td className="p-3 pl-4 font-medium text-gray-900">{h.run_label}</td>
                    <td className="text-right p-3 font-mono text-gray-700">{fmt(h.gross_pay)}</td>
                    <td className="text-right p-3 font-mono text-red-600">{fmt(h.nssf_employee)}</td>
                    <td className="text-right p-3 font-mono text-red-600">{fmt(h.paye)}</td>
                    <td className="text-right p-3 pr-4 font-mono font-semibold text-blue-700">{fmt(h.net_pay)}</td>
                    <td className="p-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLOR[h.run_status] ?? ""}`}>
                        {h.run_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Payslip Print Modal ──────────────────────────────────────────────────────

function PayslipModal({ item, runLabel, onClose }: {
  item: PayrollItem; runLabel: string; onClose: () => void;
}) {
  const printRef = useRef<HTMLDivElement>(null);

  const print = () => {
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`<html><head><title>Payslip — ${runLabel}</title>
      <style>
        body{font-family:Arial,sans-serif;font-size:13px;margin:32px;color:#111}
        h1{font-size:18px;margin-bottom:4px} .sub{font-size:14px;color:#555;margin-bottom:16px}
        table{width:100%;border-collapse:collapse;margin-top:12px}
        th{background:#f3f4f6;text-align:left;padding:6px 10px;font-size:12px}
        td{padding:5px 10px;border-bottom:1px solid #e5e7eb}
        .section-head td{font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:8px 10px 4px}
        .earn .section-head td{background:#f0fdf4;color:#166534}
        .ded .section-head td{background:#fef2f2;color:#991b1b}
        .subtotal td{font-weight:700;background:#f9fafb}
        .net td{font-weight:700;font-size:15px;color:#1d4ed8;background:#eff6ff;padding:8px 10px}
        .info{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:16px;font-size:13px}
        .info span{color:#555}
        .sig{margin-top:48px;display:flex;justify-content:space-between}
        .sig-line{border-top:1px solid #111;width:180px;text-align:center;padding-top:4px;font-size:11px}
      </style></head><body>${printRef.current?.innerHTML ?? ""}</body></html>`);
    win.document.close();
    win.print();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold text-gray-900">Payslip — {runLabel}</h2>
          <div className="flex gap-2">
            <button onClick={print}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 rounded-lg hover:bg-gray-200">
              <Printer size={14} /> Print
            </button>
            <button onClick={onClose}><X size={20} /></button>
          </div>
        </div>

        <div ref={printRef} className="p-6">
          <h1 className="text-xl font-bold text-gray-900">PAYSLIP</h1>
          <p className="sub text-gray-500 text-sm mb-4">{runLabel}</p>

          <div className="grid grid-cols-2 gap-1 text-sm mb-5">
            <div><span className="text-gray-500">Name: </span>
              <strong>{item.first_name} {item.last_name}</strong></div>
            <div><span className="text-gray-500">Employee No: </span>
              <strong>{item.employee_no}</strong></div>
            <div><span className="text-gray-500">Designation: </span>
              {item.subject_specialization || "—"}</div>
            {item.prorate_pct < 100 && (
              <div><span className="text-gray-500">Pro-rated: </span>
                <strong>{item.prorate_pct}% of full month</strong></div>
            )}
          </div>

          <div className="table-scroll"><table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
            <tbody>
              <tr className="earn section-head">
                <td colSpan={2} className="p-2 pl-3 text-xs font-semibold text-green-700 uppercase tracking-wide bg-green-50">
                  Earnings
                </td>
              </tr>
              {(
                [
                  ["Basic Salary", item.basic_salary],
                  ...(item.housing_allow > 0   ? [["Housing Allowance",   item.housing_allow]]   : []),
                  ...(item.transport_allow > 0  ? [["Transport Allowance", item.transport_allow]]  : []),
                  ...(item.other_allow > 0      ? [["Other Allowances",    item.other_allow]]      : []),
                ] as [string, number][]
              ).map(([label, val]) => (
                <tr key={label}>
                  <td className="p-2 pl-3 text-gray-600">{label}</td>
                  <td className="text-right font-mono p-2 pr-3">{fmtN(val)}</td>
                </tr>
              ))}
              <tr className="bg-green-50">
                <td className="p-2 pl-3 font-semibold">Gross Pay</td>
                <td className="text-right font-mono font-semibold p-2 pr-3">{fmtN(item.gross_pay)}</td>
              </tr>

              <tr className="ded section-head">
                <td colSpan={2} className="p-2 pl-3 text-xs font-semibold text-red-700 uppercase tracking-wide bg-red-50">
                  Deductions
                </td>
              </tr>
              {(
                [
                  ["NSSF Employee (10%)", item.nssf_employee],
                  ["PAYE Tax",            item.paye],
                  ...(item.loan_deduction > 0 ? [["Loan Deduction",          item.loan_deduction]] : []),
                  ...(item.loan_board > 0     ? [["Loan Board / HESLB (15%)", item.loan_board]]    : []),
                ] as [string, number][]
              ).map(([label, val]) => (
                <tr key={label}>
                  <td className="p-2 pl-3 text-gray-600">{label}</td>
                  <td className="text-right font-mono p-2 pr-3 text-red-600">{fmtN(val)}</td>
                </tr>
              ))}
              <tr className="bg-red-50">
                <td className="p-2 pl-3 font-semibold">Total Deductions</td>
                <td className="text-right font-mono font-semibold text-red-600 p-2 pr-3">
                  {fmtN(item.total_deductions)}
                </td>
              </tr>

              <tr className="net bg-blue-50">
                <td className="p-2 pl-3 font-bold text-blue-800 text-base">NET PAY</td>
                <td className="text-right font-mono font-bold text-blue-800 text-base p-2 pr-3">
                  {fmtN(item.net_pay)}
                </td>
              </tr>
            </tbody>
          </table></div>

          <div className="sig mt-12 flex justify-between">
            <div className="sig-line text-center">
              <div className="h-10" />
              <div className="text-xs text-gray-500">Employee Signature</div>
            </div>
            <div className="sig-line text-center">
              <div className="h-10" />
              <div className="text-xs text-gray-500">Authorized Signature</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Payroll Register Print ───────────────────────────────────────────────────

function printRegister(items: PayrollItem[], run: PayrollRun) {
  const rows = items.map((it, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${it.employee_no}</td>
      <td>${it.first_name} ${it.last_name}</td>
      <td class="n">${fmtN(it.gross_pay)}</td>
      <td class="n">${fmtN(it.nssf_employee)}</td>
      <td class="n">${fmtN(it.nssf_employer)}</td>
      <td class="n">${fmtN(it.paye)}</td>
      <td class="n">${fmtN(it.loan_deduction + it.loan_board)}</td>
      <td class="n tot">${fmtN(it.total_deductions)}</td>
      <td class="n net">${fmtN(it.net_pay)}</td>
      ${it.prorate_pct < 100 ? `<td class="n">${it.prorate_pct}%</td>` : "<td></td>"}
    </tr>`).join("");

  const tGross = items.reduce((s, i) => s + i.gross_pay, 0);
  const tNssfe = items.reduce((s, i) => s + i.nssf_employee, 0);
  const tNssfer = items.reduce((s, i) => s + i.nssf_employer, 0);
  const tPaye  = items.reduce((s, i) => s + i.paye, 0);
  const tOther = items.reduce((s, i) => s + i.loan_deduction + i.loan_board, 0);
  const tDed   = items.reduce((s, i) => s + i.total_deductions, 0);
  const tNet   = items.reduce((s, i) => s + i.net_pay, 0);

  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`<html><head><title>Payroll Register — ${run.label}</title>
    <style>
      body{font-family:Arial,sans-serif;font-size:11px;margin:24px;color:#111}
      h1{font-size:16px;margin:0} .sub{color:#555;margin-bottom:16px;font-size:12px}
      table{width:100%;border-collapse:collapse}
      th{background:#1e40af;color:#fff;text-align:right;padding:5px 6px;font-size:10px;white-space:nowrap}
      th:nth-child(1),th:nth-child(2),th:nth-child(3){text-align:left}
      td{padding:4px 6px;border-bottom:1px solid #e5e7eb;white-space:nowrap}
      td.n{text-align:right;font-family:monospace}
      td.tot{background:#fef2f2;font-weight:700;color:#b91c1c}
      td.net{background:#eff6ff;font-weight:700;color:#1d4ed8}
      tr.total td{font-weight:700;background:#f3f4f6;border-top:2px solid #1e40af}
      tr.total td.net{background:#dbeafe}
      tr:nth-child(even){background:#f9fafb}
      .sig{margin-top:40px;display:flex;justify-content:space-between}
      .sig-line{border-top:1px solid #111;width:200px;text-align:center;padding-top:4px;font-size:10px}
      @media print{body{margin:8px}}
    </style></head><body>
    <h1>PAYROLL REGISTER</h1>
    <p class="sub">${run.label} &nbsp;|&nbsp; ${items.length} employees &nbsp;|&nbsp; Status: ${run.status.toUpperCase()}</p>
    <div className="table-scroll"><table>
      <thead><tr>
        <th>#</th><th>Emp No</th><th>Name</th>
        <th>Gross Pay</th><th>NSSF Emp</th><th>NSSF Er</th>
        <th>PAYE</th><th>Other Ded.</th><th>Total Ded.</th><th>Net Pay</th><th>%</th>
      </tr></thead>
      <tbody>${rows}
        <tr class="total">
          <td colspan="3">TOTAL (${items.length} employees)</td>
          <td class="n">${fmtN(tGross)}</td>
          <td class="n">${fmtN(tNssfe)}</td>
          <td class="n">${fmtN(tNssfer)}</td>
          <td class="n">${fmtN(tPaye)}</td>
          <td class="n">${fmtN(tOther)}</td>
          <td class="n tot">${fmtN(tDed)}</td>
          <td class="n net">${fmtN(tNet)}</td>
          <td></td>
        </tr>
      </tbody>
    </table></div>
    <div class="sig">
      <div class="sig-line"><br/><br/>Prepared by</div>
      <div class="sig-line"><br/><br/>Checked by</div>
      <div class="sig-line"><br/><br/>Approved by</div>
    </div>
  </body></html>`);
  win.document.close();
  win.print();
}

// ─── Pro-rate Inline Edit ─────────────────────────────────────────────────────

function ProrateCell({
  item, runId, disabled, onUpdate,
}: {
  item: PayrollItem; runId: number; disabled: boolean; onUpdate: (updated: PayrollItem) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(String(item.prorate_pct));
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const pct = parseFloat(val);
    if (isNaN(pct) || pct <= 0 || pct > 100) { setEditing(false); return; }
    setSaving(true);
    try {
      const updated = await updateProrate(runId, item.teacher_id, pct);
      onUpdate(updated);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  if (disabled) {
    return (
      <span className={item.prorate_pct < 100 ? "text-orange-600 font-medium" : "text-gray-400"}>
        {item.prorate_pct}%
      </span>
    );
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <input
          autoFocus
          type="number" min={1} max={100}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          className="w-16 border rounded px-1 py-0.5 text-xs text-center"
        />
        <span className="text-xs">%</span>
        <button onClick={save} disabled={saving}
          className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50">
          {saving ? "…" : "✓"}
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => { setVal(String(item.prorate_pct)); setEditing(true); }}
      className={`text-sm hover:underline ${item.prorate_pct < 100 ? "text-orange-600 font-medium" : "text-gray-400 hover:text-gray-700"}`}
      title="Click to change pro-rate"
    >
      {item.prorate_pct}%
    </button>
  );
}

// ─── Run Detail Modal ─────────────────────────────────────────────────────────

type RunSubTab = "payslips" | "nssf" | "paye" | "bank";

function RunDetailModal({ run: initialRun, onClose, onRefresh }: {
  run: PayrollRun; onClose: () => void; onRefresh: () => void;
}) {
  const { can } = useAuthStore();
  const [run, setRun] = useState(initialRun);
  const [items, setItems] = useState<PayrollItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [err, setErr] = useState("");
  const [printItem, setPrintItem] = useState<PayrollItem | null>(null);
  const [subTab, setSubTab] = useState<RunSubTab>("payslips");

  const load = () => {
    setLoading(true);
    getRunItems(run.id)
      .then((d) => { setItems(d.items); setRun(d.run as PayrollRun); })
      .finally(() => setLoading(false));
  };

  useEffect(load, [run.id]);

  const action = async (fn: () => Promise<any>, label: string) => {
    setWorking(true); setErr("");
    try { await fn(); onRefresh(); load(); }
    catch (e: any) { setErr(e?.response?.data?.detail ?? `${label} failed`); }
    finally { setWorking(false); }
  };

  const updateItem = (updated: PayrollItem) => {
    setItems((prev) => prev.map((it) => it.teacher_id === updated.teacher_id ? updated : it));
  };

  const isDraft = run.status === "draft";
  const canManage = can("payroll.manage");

  const totalGross = items.reduce((s, i) => s + i.gross_pay, 0);
  const totalNssfe = items.reduce((s, i) => s + i.nssf_employee, 0);
  const totalNssfer = items.reduce((s, i) => s + i.nssf_employer, 0);
  const totalPaye  = items.reduce((s, i) => s + i.paye, 0);
  const totalNet   = items.reduce((s, i) => s + i.net_pay, 0);
  const totalDed   = items.reduce((s, i) => s + i.total_deductions, 0);

  const SUB_TABS: { key: RunSubTab; label: string }[] = [
    { key: "payslips", label: "Payslips" },
    { key: "nssf",     label: "NSSF Report" },
    { key: "paye",     label: "PAYE Return" },
    { key: "bank",     label: "Bank List" },
  ];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col">
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

        {/* action bar */}
        <div className="flex gap-2 px-4 py-2.5 border-b bg-gray-50 shrink-0 flex-wrap items-center">
          {canManage && isDraft && (
            <button onClick={() => action(() => computeRun(run.id), "Compute")}
              disabled={working}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              <PlayCircle size={14} />
              {items.length ? "Recompute" : "Compute Payroll"}
            </button>
          )}
          {canManage && isDraft && items.length > 0 && (
            <button onClick={() => action(() => finalizeRun(run.id), "Finalize")}
              disabled={working}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              <CheckCircle size={14} /> Finalize
            </button>
          )}
          {canManage && run.status === "finalized" && (
            <button onClick={() => action(() => reopenRun(run.id), "Reopen")}
              disabled={working}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50">
              <RotateCcw size={14} /> Reopen
            </button>
          )}
          {run.status === "finalized" && can("payroll.approve") && (
            <button onClick={() => action(() => approveRun(run.id), "Approve")}
              disabled={working}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
              <CheckCircle size={14} /> Approve & Post to Ledger
            </button>
          )}

          {items.length > 0 && (
            <div className="ml-auto flex gap-1.5">
              <button onClick={() => printRegister(items, run)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-white">
                <Printer size={14} /> Register
              </button>
              <button onClick={() => exportRegisterCSV(items, run)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-white">
                <Download size={14} /> Excel
              </button>
            </div>
          )}

          {err && (
            <p className="text-red-600 text-sm flex items-center gap-1 w-full">
              <AlertCircle size={14} /> {err}
            </p>
          )}
        </div>

        {/* summary */}
        {items.length > 0 && (
          <div className="grid grid-cols-6 gap-px bg-gray-200 border-b shrink-0">
            {[
              ["Employees", items.length, false],
              ["Gross Pay", totalGross, true],
              ["NSSF (both)", totalNssfe + totalNssfer, true],
              ["PAYE", totalPaye, true],
              ["Total Deductions", totalDed, true],
              ["Net Pay", totalNet, true],
            ].map(([label, val, money]) => (
              <div key={label as string} className="bg-white p-2.5 text-center">
                <div className="text-xs text-gray-500">{label}</div>
                <div className="font-semibold text-gray-900 text-xs mt-0.5">
                  {money ? fmt(val as number) : val}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* sub-tabs */}
        {items.length > 0 && (
          <div className="flex gap-0.5 px-4 border-b bg-white shrink-0">
            {SUB_TABS.map((t) => (
              <button key={t.key} onClick={() => setSubTab(t.key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  subTab === t.key
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-gray-500 hover:text-gray-800"
                }`}>
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* content */}
        <div className="overflow-auto flex-1">
          {loading ? (
            <div className="p-8 text-center text-gray-400">Loading…</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No payslips yet. Click "Compute Payroll" to generate.
            </div>
          ) : subTab === "payslips" ? (
            <div className="table-scroll"><table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-2 pl-4 font-medium text-gray-600">Employee</th>
                  <th className="text-right p-2 font-medium text-gray-600">Gross</th>
                  <th className="text-right p-2 font-medium text-gray-600">NSSF</th>
                  <th className="text-right p-2 font-medium text-gray-600">PAYE</th>
                  <th className="text-right p-2 font-medium text-gray-600">Other</th>
                  <th className="text-right p-2 pr-4 font-medium text-gray-600">Net Pay</th>
                  <th className="text-center p-2 font-medium text-gray-600">%</th>
                  <th className="p-2 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="p-2 pl-4">
                      <div className="font-medium text-gray-900">{item.first_name} {item.last_name}</div>
                      <div className="text-xs text-gray-400">{item.employee_no}</div>
                    </td>
                    <td className="text-right p-2 font-mono text-gray-700">{fmt(item.gross_pay)}</td>
                    <td className="text-right p-2 font-mono text-red-600">{fmt(item.nssf_employee)}</td>
                    <td className="text-right p-2 font-mono text-red-600">{fmt(item.paye)}</td>
                    <td className="text-right p-2 font-mono text-red-600">
                      {fmt(item.loan_deduction + item.loan_board)}
                    </td>
                    <td className="text-right p-2 pr-4 font-mono font-semibold text-blue-700">
                      {fmt(item.net_pay)}
                    </td>
                    <td className="text-center p-2">
                      <ProrateCell
                        item={item} runId={run.id}
                        disabled={!isDraft || !canManage}
                        onUpdate={updateItem}
                      />
                    </td>
                    <td className="p-2">
                      <button onClick={() => setPrintItem(item)}
                        className="text-gray-400 hover:text-gray-700" title="View payslip">
                        <FileText size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>

          ) : subTab === "nssf" ? (
            <div>
              <div className="flex justify-end px-4 py-2 border-b">
                <button onClick={() => exportNSSFCSV(items, run)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
                  <Download size={14} /> Export CSV
                </button>
              </div>
              <div className="table-scroll"><table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 pl-4 font-medium text-gray-600">#</th>
                    <th className="text-left p-3 font-medium text-gray-600">Employee</th>
                    <th className="text-right p-3 font-medium text-gray-600">Gross Pay</th>
                    <th className="text-right p-3 font-medium text-gray-600">Employee 10%</th>
                    <th className="text-right p-3 font-medium text-gray-600">Employer 10%</th>
                    <th className="text-right p-3 pr-4 font-medium text-gray-600">Total NSSF</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((it, i) => (
                    <tr key={it.id} className="hover:bg-gray-50">
                      <td className="p-3 pl-4 text-gray-400">{i + 1}</td>
                      <td className="p-3">
                        <div className="font-medium">{it.first_name} {it.last_name}</div>
                        <div className="text-xs text-gray-400">{it.employee_no}</div>
                      </td>
                      <td className="text-right p-3 font-mono">{fmt(it.gross_pay)}</td>
                      <td className="text-right p-3 font-mono text-blue-700">{fmt(it.nssf_employee)}</td>
                      <td className="text-right p-3 font-mono text-blue-700">{fmt(it.nssf_employer)}</td>
                      <td className="text-right p-3 pr-4 font-mono font-semibold">
                        {fmt(it.nssf_employee + it.nssf_employer)}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 font-semibold border-t-2 border-gray-300">
                    <td className="p-3 pl-4" colSpan={2}>TOTAL</td>
                    <td className="text-right p-3 font-mono">{fmt(totalGross)}</td>
                    <td className="text-right p-3 font-mono text-blue-700">{fmt(totalNssfe)}</td>
                    <td className="text-right p-3 font-mono text-blue-700">{fmt(totalNssfer)}</td>
                    <td className="text-right p-3 pr-4 font-mono">{fmt(totalNssfe + totalNssfer)}</td>
                  </tr>
                </tbody>
              </table></div>
            </div>

          ) : subTab === "paye" ? (
            <div>
              <div className="flex justify-end px-4 py-2 border-b">
                <button onClick={() => exportPAYECSV(items, run)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
                  <Download size={14} /> Export CSV
                </button>
              </div>
              <div className="table-scroll"><table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 pl-4 font-medium text-gray-600">#</th>
                    <th className="text-left p-3 font-medium text-gray-600">Employee</th>
                    <th className="text-right p-3 font-medium text-gray-600">Gross Pay</th>
                    <th className="text-right p-3 font-medium text-gray-600">NSSF Deducted</th>
                    <th className="text-right p-3 font-medium text-gray-600">Taxable Income</th>
                    <th className="text-right p-3 pr-4 font-medium text-gray-600">PAYE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((it, i) => (
                    <tr key={it.id} className="hover:bg-gray-50">
                      <td className="p-3 pl-4 text-gray-400">{i + 1}</td>
                      <td className="p-3">
                        <div className="font-medium">{it.first_name} {it.last_name}</div>
                        <div className="text-xs text-gray-400">{it.employee_no}</div>
                      </td>
                      <td className="text-right p-3 font-mono">{fmt(it.gross_pay)}</td>
                      <td className="text-right p-3 font-mono text-gray-500">{fmt(it.nssf_employee)}</td>
                      <td className="text-right p-3 font-mono">{fmt(it.gross_pay - it.nssf_employee)}</td>
                      <td className="text-right p-3 pr-4 font-mono font-semibold text-red-600">{fmt(it.paye)}</td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 font-semibold border-t-2 border-gray-300">
                    <td className="p-3 pl-4" colSpan={2}>TOTAL</td>
                    <td className="text-right p-3 font-mono">{fmt(totalGross)}</td>
                    <td className="text-right p-3 font-mono text-gray-500">{fmt(totalNssfe)}</td>
                    <td className="text-right p-3 font-mono">{fmt(totalGross - totalNssfe)}</td>
                    <td className="text-right p-3 pr-4 font-mono text-red-600">{fmt(totalPaye)}</td>
                  </tr>
                </tbody>
              </table></div>
            </div>

          ) : subTab === "bank" ? (
            <div>
              <div className="flex items-center justify-between px-4 py-2 border-b">
                <p className="text-sm text-gray-500">
                  Bank transfer list — {items.length} employees · Total:{" "}
                  <strong className="text-gray-900">{fmt(totalNet)}</strong>
                </p>
                <button onClick={() => exportBankListCSV(items, run)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
                  <Download size={14} /> Export CSV
                </button>
              </div>
              <div className="table-scroll"><table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 pl-4 font-medium text-gray-600">#</th>
                    <th className="text-left p-3 font-medium text-gray-600">Employee No</th>
                    <th className="text-left p-3 font-medium text-gray-600">Name</th>
                    <th className="text-right p-3 pr-4 font-medium text-gray-600">Net Pay (TZS)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((it, i) => (
                    <tr key={it.id} className="hover:bg-gray-50">
                      <td className="p-3 pl-4 text-gray-400">{i + 1}</td>
                      <td className="p-3 font-mono text-gray-700">{it.employee_no}</td>
                      <td className="p-3 font-medium">{it.first_name} {it.last_name}</td>
                      <td className="text-right p-3 pr-4 font-mono font-semibold text-blue-700">{fmt(it.net_pay)}</td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 font-semibold border-t-2 border-gray-300">
                    <td colSpan={3} className="p-3 pl-4">TOTAL</td>
                    <td className="text-right p-3 pr-4 font-mono text-blue-700">{fmt(totalNet)}</td>
                  </tr>
                </tbody>
              </table></div>
            </div>
          ) : null}
        </div>
      </div>

      {printItem && (
        <PayslipModal item={printItem} runLabel={run.label} onClose={() => setPrintItem(null)} />
      )}
    </div>
  );
}

// ─── YTD Tab ──────────────────────────────────────────────────────────────────

function YTDTab() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [rows, setRows] = useState<YTDRow[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getYTD(year).then(setRows).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [year]);

  const exportYTD = () => {
    const header = [
      "Employee No", "Name", "Months Paid", "YTD Gross",
      "YTD NSSF Employee", "YTD NSSF Employer", "YTD PAYE",
      "YTD Loan", "YTD Loan Board", "YTD Deductions", "YTD Net Pay",
    ];
    const data = rows.map((r) => [
      r.employee_no, `${r.first_name} ${r.last_name}`,
      String(r.months_paid), String(r.ytd_gross),
      String(r.ytd_nssf_employee), String(r.ytd_nssf_employer),
      String(r.ytd_paye), String(r.ytd_loan), String(r.ytd_loan_board),
      String(r.ytd_deductions), String(r.ytd_net),
    ]);
    downloadCSV(`YTD_${year}.csv`, [header, ...data]);
  };

  const tGross = rows.reduce((s, r) => s + r.ytd_gross, 0);
  const tNet   = rows.reduce((s, r) => s + r.ytd_net, 0);
  const tPaye  = rows.reduce((s, r) => s + r.ytd_paye, 0);
  const tNssf  = rows.reduce((s, r) => s + r.ytd_nssf_employee + r.ytd_nssf_employer, 0);

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-gray-600">Year-to-Date Summary</h2>
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}
            className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none">
            {[2023, 2024, 2025, 2026, 2027].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        {rows.length > 0 && (
          <button onClick={exportYTD}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            <Download size={14} /> Export CSV
          </button>
        )}
      </div>

      {rows.length > 0 && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            ["Total Gross", fmt(tGross)],
            ["Total NSSF", fmt(tNssf)],
            ["Total PAYE", fmt(tPaye)],
            ["Total Net Pay", fmt(tNet)],
          ].map(([label, val]) => (
            <div key={label as string} className="bg-white rounded-xl border p-4">
              <div className="text-xs text-gray-500">{label} ({year})</div>
              <div className="text-lg font-bold text-gray-900 mt-1">{val}</div>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-dashed">
          No finalized payroll data for {year}.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="table-scroll"><table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 pl-4 font-medium text-gray-600">Employee</th>
                <th className="text-center p-3 font-medium text-gray-600">Months</th>
                <th className="text-right p-3 font-medium text-gray-600">YTD Gross</th>
                <th className="text-right p-3 font-medium text-gray-600">YTD NSSF</th>
                <th className="text-right p-3 font-medium text-gray-600">YTD PAYE</th>
                <th className="text-right p-3 font-medium text-gray-600">YTD Other</th>
                <th className="text-right p-3 pr-4 font-medium text-gray-600">YTD Net Pay</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((r) => (
                <tr key={r.teacher_id} className="hover:bg-gray-50">
                  <td className="p-3 pl-4">
                    <div className="font-medium text-gray-900">{r.first_name} {r.last_name}</div>
                    <div className="text-xs text-gray-400">{r.employee_no}</div>
                  </td>
                  <td className="text-center p-3 text-gray-600">{r.months_paid}</td>
                  <td className="text-right p-3 font-mono text-gray-700">{fmt(r.ytd_gross)}</td>
                  <td className="text-right p-3 font-mono text-gray-600">
                    {fmt(r.ytd_nssf_employee + r.ytd_nssf_employer)}
                  </td>
                  <td className="text-right p-3 font-mono text-red-600">{fmt(r.ytd_paye)}</td>
                  <td className="text-right p-3 font-mono text-gray-600">
                    {fmt(r.ytd_loan + r.ytd_loan_board)}
                  </td>
                  <td className="text-right p-3 pr-4 font-mono font-semibold text-blue-700">
                    {fmt(r.ytd_net)}
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold border-t-2 border-gray-300">
                <td className="p-3 pl-4" colSpan={2}>TOTAL</td>
                <td className="text-right p-3 font-mono">{fmt(tGross)}</td>
                <td className="text-right p-3 font-mono">{fmt(tNssf)}</td>
                <td className="text-right p-3 font-mono text-red-600">{fmt(tPaye)}</td>
                <td className="text-right p-3 font-mono">
                  {fmt(rows.reduce((s, r) => s + r.ytd_loan + r.ytd_loan_board, 0))}
                </td>
                <td className="text-right p-3 pr-4 font-mono text-blue-700">{fmt(tNet)}</td>
              </tr>
            </tbody>
          </table></div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PayrollPage() {
  const { can } = useAuthStore();
  const [tab, setTab] = useState<"runs" | "staff" | "ytd">("runs");

  // runs
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<PayrollRun | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newMonth, setNewMonth] = useState(new Date().getMonth() + 1);
  const [newYear, setNewYear]   = useState(new Date().getFullYear());
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);

  // staff
  const [staff, setStaff] = useState<StaffSalary[]>([]);
  const [staffSearch, setStaffSearch] = useState("");
  const [staffLoading, setStaffLoading] = useState(false);
  const [editStaff, setEditStaff] = useState<StaffSalary | null>(null);
  const [historyStaff, setHistoryStaff] = useState<StaffSalary | null>(null);

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

  const handleCreate = async () => {
    setCreating(true); setCreateErr("");
    try {
      await createPayrollRun(newMonth, newYear);
      setShowCreate(false);
      loadRuns();
    } catch (e: any) {
      setCreateErr(e?.response?.data?.detail ?? "Failed to create run");
    } finally { setCreating(false); }
  };

  const handleDelete = async (run: PayrollRun) => {
    if (!confirm(`Delete "${run.label}" payroll run? This cannot be undone.`)) return;
    setDeleting(run.id);
    try { await deletePayrollRun(run.id); loadRuns(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Delete failed"); }
    finally { setDeleting(null); }
  };

  const configuredCount = staff.filter((s) => s.basic_salary != null).length;

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="bg-white border-b px-6 py-4">
        <h1 className="text-xl font-bold text-gray-900">Payroll</h1>
        <p className="text-sm text-gray-500">Monthly payroll processing · TRA 2024/25 PAYE · NSSF · HESLB</p>
      </div>

      {/* tabs */}
      <div className="bg-white border-b px-6 flex gap-1">
        {([
          { key: "runs",  label: "Payroll Runs",   icon: Calendar },
          { key: "staff", label: "Staff Salaries",  icon: Users },
          { key: "ytd",   label: "Year-to-Date",    icon: History },
        ] as { key: typeof tab; label: string; icon: any }[]).map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-6">

        {/* ── Runs ── */}
        {tab === "runs" && (
          <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">{runs.length} payroll run{runs.length !== 1 ? "s" : ""}</p>
              {can("payroll.manage") && (
                <button onClick={() => setShowCreate(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  <Plus size={14} /> New Run
                </button>
              )}
            </div>

            {showCreate && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 flex items-end gap-3 flex-wrap">
                <div>
                  <label className="text-xs text-gray-600 font-medium">Month</label>
                  <select value={newMonth} onChange={(e) => setNewMonth(Number(e.target.value))}
                    className="mt-1 block border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none">
                    {MONTHS.slice(1).map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-600 font-medium">Year</label>
                  <input type="number" value={newYear}
                    onChange={(e) => setNewYear(Number(e.target.value))}
                    className="mt-1 block w-28 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <button onClick={handleCreate} disabled={creating}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {creating ? "Creating…" : "Create"}
                </button>
                <button onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-white">Cancel</button>
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
                No payroll runs yet.
              </div>
            ) : (
              <div className="bg-white rounded-xl border divide-y">
                {runs.map((run) => (
                  <div key={run.id} className="flex items-center justify-between px-5 py-4 hover:bg-gray-50">
                    <button onClick={() => setSelectedRun(run)} className="flex-1 flex items-center gap-4 text-left">
                      <div>
                        <div className="font-medium text-gray-900">{run.label}</div>
                        <div className="text-xs text-gray-400">
                          {run.employee_count} employee{run.employee_count !== 1 ? "s" : ""}
                          {run.total_gross != null && ` · Gross: ${fmt(run.total_gross)}`}
                          {run.total_net != null && ` · Net: ${fmt(run.total_net)}`}
                        </div>
                      </div>
                    </button>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLOR[run.status]}`}>
                        {run.status}
                      </span>
                      {can("payroll.manage") && run.status === "draft" && (
                        <button
                          onClick={() => handleDelete(run)}
                          disabled={deleting === run.id}
                          className="text-gray-300 hover:text-red-500 transition-colors disabled:opacity-50"
                          title="Delete draft run">
                          <Trash2 size={15} />
                        </button>
                      )}
                      <ChevronRight size={16} className="text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Staff ── */}
        {tab === "staff" && (
          <div className="max-w-5xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">
                {configuredCount}/{staff.length} employees configured
              </p>
              <input type="text" placeholder="Search staff…" value={staffSearch}
                onChange={(e) => setStaffSearch(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none w-56" />
            </div>

            {staffLoading ? (
              <div className="text-center text-gray-400 py-12">Loading…</div>
            ) : (
              <div className="bg-white rounded-xl border overflow-hidden">
                <div className="table-scroll"><table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left p-3 pl-4 font-medium text-gray-600">Employee</th>
                      <th className="text-right p-3 font-medium text-gray-600">Basic</th>
                      <th className="text-right p-3 font-medium text-gray-600">Allowances</th>
                      <th className="text-right p-3 font-medium text-gray-600">Gross</th>
                      <th className="text-right p-3 font-medium text-gray-600">Loan Ded.</th>
                      <th className="p-3 text-center font-medium text-gray-600">HESLB</th>
                      <th className="p-3 w-16" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {staff.map((s) => {
                      const gross = (s.basic_salary ?? 0) + (s.housing_allow ?? 0)
                        + (s.transport_allow ?? 0) + (s.other_allow ?? 0);
                      const configured = s.basic_salary != null;
                      return (
                        <tr key={s.id} className="hover:bg-gray-50">
                          <td className="p-3 pl-4">
                            <div className="font-medium text-gray-900">{s.first_name} {s.last_name}</div>
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
                            {configured && s.loan_deduction ? fmt(s.loan_deduction) : "—"}
                          </td>
                          <td className="text-center p-3">
                            {s.loan_board ? (
                              <span className="text-xs text-orange-600 font-medium">Yes</span>
                            ) : (
                              <span className="text-xs text-gray-300">No</span>
                            )}
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-2 justify-end">
                              <button onClick={() => setHistoryStaff(s)}
                                className="text-gray-400 hover:text-gray-700" title="View history">
                                <History size={14} />
                              </button>
                              {can("payroll.manage") && (
                                <button onClick={() => setEditStaff(s)}
                                  className="text-blue-400 hover:text-blue-700" title="Configure salary">
                                  <Edit2 size={14} />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {staff.length === 0 && (
                      <tr>
                        <td colSpan={7} className="text-center text-gray-400 py-8">No active staff found.</td>
                      </tr>
                    )}
                  </tbody>
                </table></div>
              </div>
            )}
          </div>
        )}

        {/* ── YTD ── */}
        {tab === "ytd" && <YTDTab />}
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
        <SalaryDialog staff={editStaff} onClose={() => setEditStaff(null)} onSave={loadStaff} />
      )}
      {historyStaff && (
        <HistoryModal staff={historyStaff} onClose={() => setHistoryStaff(null)} />
      )}
    </div>
  );
}
