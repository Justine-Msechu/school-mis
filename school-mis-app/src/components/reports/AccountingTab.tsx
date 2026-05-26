import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { Download } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import {
  getFeeCollectionByClass, getMonthlyIncome, getExpenseBreakdown, getIncomeVsExpense,
  type FeeByClassRow, type IncomeVsExpenseRow, type ExpenseBreakdownRow, type OutstandingRow, type LedgerEntry,
} from "@/api/reports";
import { getAcademicYears, type AcademicYear } from "@/api/settings";
import api from "@/api/client";

type AccTab = "fee-collection" | "outstanding" | "income" | "ledger";

const TZS = (n: number) => `TZS ${Math.round(n ?? 0).toLocaleString()}`;
const INPUT = "h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white";
const PIE_COLORS = ["#7C3AED", "#0891B2", "#059669", "#D97706", "#E11D48", "#6366F1", "#0EA5E9", "#84CC16"];

interface ClassItem { id: number; name: string }

export default function AccountingTab() {
  const [sub, setSub] = useState<AccTab>("fee-collection");

  const [years, setYears]   = useState<AcademicYear[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);

  // Fee Collection
  const [feeRows, setFeeRows]     = useState<FeeByClassRow[]>([]);
  const [feeYearId, setFeeYearId] = useState<number | "">("");
  const [feeTerm, setFeeTerm]     = useState<number | "">("");
  const [feeLoading, setFeeLoading] = useState(false);

  // Outstanding
  const [outstanding, setOutstanding]   = useState<OutstandingRow[]>([]);
  const [outYearId, setOutYearId]       = useState<number | "">("");
  const [outClassId, setOutClassId]     = useState<number | "">("");
  const [outLoading, setOutLoading]     = useState(false);

  // Income Summary
  const [incVsExp, setIncVsExp]           = useState<IncomeVsExpenseRow[]>([]);
  const [expBreakdown, setExpBreakdown]   = useState<ExpenseBreakdownRow[]>([]);
  const [incYear, setIncYear]             = useState(new Date().getFullYear());
  const [incLoading, setIncLoading]       = useState(false);

  // Ledger
  const [ledger, setLedger]         = useState<LedgerEntry[]>([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  useEffect(() => {
    getAcademicYears()
      .then((yrs) => {
        setYears(yrs);
        const cur = yrs.find((y) => y.is_current);
        if (cur) { setFeeYearId(cur.id); setOutYearId(cur.id); }
      })
      .catch(() => {});
    api.get("/grades/classes")
      .then(({ data }) => setClasses(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  // ── load fee collection ──────────────────────────────────────────────────────
  useEffect(() => {
    if (sub !== "fee-collection") return;
    setFeeLoading(true);
    getFeeCollectionByClass(feeYearId || null, feeTerm || null)
      .then(setFeeRows).catch(() => setFeeRows([]))
      .finally(() => setFeeLoading(false));
  }, [sub, feeYearId, feeTerm]);

  // ── load outstanding ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (sub !== "outstanding") return;
    setOutLoading(true);
    api.get("/finance/outstanding", {
      params: { academic_year_id: outYearId || undefined, class_id: outClassId || undefined },
    })
      .then(({ data }) => setOutstanding(Array.isArray(data) ? data : []))
      .catch(() => setOutstanding([]))
      .finally(() => setOutLoading(false));
  }, [sub, outYearId, outClassId]);

  // ── load income summary ──────────────────────────────────────────────────────
  useEffect(() => {
    if (sub !== "income") return;
    setIncLoading(true);
    Promise.all([getIncomeVsExpense(incYear), getExpenseBreakdown()])
      .then(([ive, exp]) => { setIncVsExp(ive); setExpBreakdown(exp); })
      .catch(() => {})
      .finally(() => setIncLoading(false));
  }, [sub, incYear]);

  // ── load ledger ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (sub !== "ledger") return;
    setLedgerLoading(true);
    api.get("/finance/ledger/entries", { params: { limit: 500 } })
      .then(({ data }) => setLedger(Array.isArray(data) ? data : []))
      .catch(() => setLedger([]))
      .finally(() => setLedgerLoading(false));
  }, [sub]);

  const subTabs: { key: AccTab; label: string }[] = [
    { key: "fee-collection", label: "Fee Collection" },
    { key: "outstanding",    label: "Outstanding Fees" },
    { key: "income",         label: "Income Summary" },
    { key: "ledger",         label: "Ledger" },
  ];

  return (
    <div>
      {/* sub-tab pills */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
        {subTabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setSub(t.key)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors
              ${sub === t.key ? "bg-white text-violet-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Fee Collection ─────────────────────────────────────────────────────── */}
      {sub === "fee-collection" && (
        <div className="space-y-5">
          <div className="flex gap-3 items-center flex-wrap">
            <select value={feeYearId} onChange={(e) => setFeeYearId(e.target.value ? Number(e.target.value) : "")} className={INPUT}>
              <option value="">All Years</option>
              {years.map((y) => (
                <option key={y.id} value={y.id}>{y.label}{y.is_current ? " (current)" : ""}</option>
              ))}
            </select>
            <select value={feeTerm} onChange={(e) => setFeeTerm(e.target.value ? Number(e.target.value) : "")} className={INPUT}>
              <option value="">All Terms</option>
              <option value={1}>Term 1</option>
              <option value={2}>Term 2</option>
              <option value={3}>Term 3</option>
            </select>
            {feeRows.length > 0 && (
              <button
                onClick={() => downloadCSV(
                  "Fee_Collection_By_Class",
                  ["Class", "Billed (TZS)", "Collected (TZS)", "Outstanding (TZS)", "Rate %"],
                  feeRows.map((r) => [r.class_name, r.billed, r.collected, r.outstanding,
                    r.billed > 0 ? Math.round(r.collected / r.billed * 100) : 0])
                )}
                className="ml-auto flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <Download size={14} /> Export CSV
              </button>
            )}
          </div>

          {feeLoading ? (
            <div className="h-72 bg-gray-100 rounded-xl animate-pulse" />
          ) : feeRows.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Billed vs Collected by Class</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={feeRows} margin={{ top: 4, right: 16, left: 0, bottom: 48 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="class_name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
                  <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => TZS(Number(v ?? 0))} />
                  <Legend wrapperStyle={{ paddingTop: 8 }} />
                  <Bar dataKey="billed"    name="Billed"    fill="#C4B5FD" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="collected" name="Collected" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : null}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3 text-right">Billed</th>
                  <th className="px-4 py-3 text-right">Collected</th>
                  <th className="px-4 py-3 text-right">Outstanding</th>
                  <th className="px-4 py-3 text-right">Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {feeRows.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400 text-sm">No data for the selected filters</td></tr>
                ) : feeRows.map((r, i) => {
                  const rate = r.billed > 0 ? Math.round(r.collected / r.billed * 100) : 0;
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{r.class_name}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{TZS(r.billed)}</td>
                      <td className="px-4 py-3 text-right text-emerald-700 font-medium">{TZS(r.collected)}</td>
                      <td className="px-4 py-3 text-right text-red-600">{TZS(r.outstanding)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${rate >= 80 ? "bg-emerald-500" : rate >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                              style={{ width: `${Math.min(rate, 100)}%` }}
                            />
                          </div>
                          <span className={`font-medium text-xs ${rate >= 80 ? "text-emerald-700" : rate >= 50 ? "text-amber-700" : "text-red-700"}`}>
                            {rate}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table></div>
          </div>
        </div>
      )}

      {/* ── Outstanding Fees ────────────────────────────────────────────────────── */}
      {sub === "outstanding" && (
        <div className="space-y-5">
          <div className="flex gap-3 items-center flex-wrap">
            <select value={outYearId} onChange={(e) => setOutYearId(e.target.value ? Number(e.target.value) : "")} className={INPUT}>
              <option value="">All Years</option>
              {years.map((y) => (
                <option key={y.id} value={y.id}>{y.label}{y.is_current ? " (current)" : ""}</option>
              ))}
            </select>
            <select value={outClassId} onChange={(e) => setOutClassId(e.target.value ? Number(e.target.value) : "")} className={INPUT}>
              <option value="">All Classes</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            {outstanding.length > 0 && (
              <button
                onClick={() => downloadCSV(
                  "Outstanding_Fees",
                  ["Student", "Adm No", "Class", "Billed (TZS)", "Paid (TZS)", "Balance (TZS)"],
                  outstanding.map((r) => [r.student_name, r.admission_no, r.class_name ?? "", r.total_billed, r.total_paid, r.balance])
                )}
                className="ml-auto flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <Download size={14} /> Export CSV
              </button>
            )}
          </div>

          {outstanding.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-violet-50 border border-violet-100 rounded-xl p-4">
                <p className="text-xs text-violet-600 font-medium uppercase tracking-wide">Students with balance</p>
                <p className="text-2xl font-bold text-violet-700 mt-1">{outstanding.length}</p>
              </div>
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
                <p className="text-xs text-amber-600 font-medium uppercase tracking-wide">Total billed</p>
                <p className="text-xl font-bold text-amber-700 mt-1">{TZS(outstanding.reduce((s, r) => s + r.total_billed, 0))}</p>
              </div>
              <div className="bg-red-50 border border-red-100 rounded-xl p-4">
                <p className="text-xs text-red-600 font-medium uppercase tracking-wide">Total outstanding</p>
                <p className="text-xl font-bold text-red-700 mt-1">{TZS(outstanding.reduce((s, r) => s + r.balance, 0))}</p>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Student</th>
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3 text-right">Billed</th>
                  <th className="px-4 py-3 text-right">Paid</th>
                  <th className="px-4 py-3 text-right">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {outLoading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}><td colSpan={5} className="px-4 py-3">
                      <div className="h-4 bg-gray-100 rounded animate-pulse" />
                    </td></tr>
                  ))
                ) : outstanding.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400 text-sm">No outstanding fees</td></tr>
                ) : outstanding.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{r.student_name}</div>
                      <div className="text-xs text-gray-400">{r.admission_no}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{r.class_name ?? "—"}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{TZS(r.total_billed)}</td>
                    <td className="px-4 py-3 text-right text-emerald-700">{TZS(r.total_paid)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-red-700">{TZS(r.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        </div>
      )}

      {/* ── Income Summary ──────────────────────────────────────────────────────── */}
      {sub === "income" && (
        <div className="space-y-5">
          <div className="flex gap-3 items-center">
            <select value={incYear} onChange={(e) => setIncYear(Number(e.target.value))} className={INPUT}>
              {[2023, 2024, 2025, 2026, 2027].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          {incLoading ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="h-72 bg-gray-100 rounded-xl animate-pulse" />
              <div className="h-72 bg-gray-100 rounded-xl animate-pulse" />
            </div>
          ) : (
            <div className="space-y-5">
              {incVsExp.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">Monthly Income vs Expenses ({incYear})</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={incVsExp} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v) => TZS(Number(v ?? 0))} />
                      <Legend />
                      <Bar dataKey="income"  name="Income"   fill="#7C3AED" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="expense" name="Expenses" fill="#FCA5A5" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {expBreakdown.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">Expense Breakdown by Category</h3>
                  <div className="flex items-center gap-8">
                    <div className="w-64 flex-shrink-0">
                      <ResponsiveContainer width="100%" height={240}>
                        <PieChart>
                          <Pie
                            data={expBreakdown}
                            dataKey="total"
                            nameKey="category"
                            cx="50%"
                            cy="50%"
                            outerRadius={100}
                            label={({ percent }) => `${((percent ?? 0) * 100).toFixed(0)}%`}
                            labelLine={false}
                          >
                            {expBreakdown.map((_, i) => (
                              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(v) => TZS(Number(v ?? 0))} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex-1 space-y-2.5">
                      {expBreakdown.map((r, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                            <span className="text-gray-700">{r.category}</span>
                          </div>
                          <span className="font-semibold text-gray-900">{TZS(r.total)}</span>
                        </div>
                      ))}
                      <div className="pt-2 border-t border-gray-100 flex justify-between text-sm font-bold">
                        <span className="text-gray-600">Total</span>
                        <span className="text-gray-900">{TZS(expBreakdown.reduce((s, r) => s + r.total, 0))}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {incVsExp.length === 0 && expBreakdown.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-12">No income or expense data for {incYear}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Ledger ──────────────────────────────────────────────────────────────── */}
      {sub === "ledger" && (
        <div className="space-y-4">
          <div className="flex gap-3 items-center flex-wrap">
            {ledger.length > 0 && (
              <button
                onClick={() => downloadCSV(
                  "Ledger_Entries",
                  ["Date", "Account Code", "Account Name", "Debit (TZS)", "Credit (TZS)", "Ref Type", "Ref ID", "Description"],
                  ledger.map((r) => [r.entry_date, r.account_code, r.account_name, r.debit_amount, r.credit_amount, r.reference_type, r.reference_id, r.description])
                )}
                className="ml-auto flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <Download size={14} /> Export CSV
              </button>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Account</th>
                  <th className="px-4 py-3 text-right">Debit</th>
                  <th className="px-4 py-3 text-right">Credit</th>
                  <th className="px-4 py-3">Ref</th>
                  <th className="px-4 py-3">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {ledgerLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}><td colSpan={6} className="px-4 py-3">
                      <div className="h-4 bg-gray-100 rounded animate-pulse" />
                    </td></tr>
                  ))
                ) : ledger.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400 text-sm">No ledger entries</td></tr>
                ) : ledger.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{r.entry_date}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{r.account_name}</div>
                      <div className="text-xs text-gray-400">{r.account_code}</div>
                    </td>
                    <td className="px-4 py-3 text-right text-red-700 font-medium">
                      {r.debit_amount > 0 ? TZS(r.debit_amount) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-emerald-700 font-medium">
                      {r.credit_amount > 0 ? TZS(r.credit_amount) : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                      {r.reference_type} #{r.reference_id}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{r.description || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        </div>
      )}
    </div>
  );
}
