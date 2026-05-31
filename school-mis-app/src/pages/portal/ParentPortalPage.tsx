import { useEffect, useState } from "react";
import { BookOpen, Calendar, DollarSign, FileText, Plus, Users } from "lucide-react";
import {
  getParentChildren, getChildGrades, getChildFees, getChildAttendance, getChildLeave, submitLeave,
  type PortalChild, type PortalGrade, type ChildFeeSummary, type AttendanceResponse, type LeaveRequest,
} from "@/api/portal";

type ChildTab = "grades" | "fees" | "attendance" | "leave";

const TZS = (n: number) => `TZS ${(n ?? 0).toLocaleString()}`;
const fmt = (n: number) => n ?? 0;

function GradesPanel({ studentId }: { studentId: number }) {
  const [grades, setGrades] = useState<PortalGrade[] | null>(null);

  useEffect(() => {
    getChildGrades(studentId).then(setGrades).catch(() => setGrades([]));
  }, [studentId]);

  if (!grades) return <Spinner />;
  if (grades.length === 0) return <Empty text="No approved grades yet." />;

  const exams: Record<string, PortalGrade[]> = {};
  for (const g of grades) {
    const key = `${g.year_label ?? ""} — ${g.exam_name} (${g.term})`;
    if (!exams[key]) exams[key] = [];
    exams[key].push(g);
  }

  return (
    <div className="space-y-5">
      {Object.entries(exams).map(([exam, rows]) => (
        <div key={exam}>
          <h4 className="text-sm font-semibold text-gray-600 mb-2">{exam}</h4>
          <Table
            headers={["Subject", "Score", "Grade"]}
            rows={rows.map(g => [
              g.subject_name,
              `${fmt(g.score)}/${fmt(g.max_score)}`,
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                g.grade_letter === "A" ? "bg-green-100 text-green-700" :
                g.grade_letter === "B" ? "bg-blue-100 text-blue-700" :
                g.grade_letter === "C" ? "bg-yellow-100 text-yellow-700" :
                "bg-red-100 text-red-700"
              }`}>{g.grade_letter ?? "—"}</span>,
            ])}
          />
        </div>
      ))}
    </div>
  );
}

function FeesPanel({ studentId }: { studentId: number }) {
  const [data, setData] = useState<ChildFeeSummary | null>(null);

  useEffect(() => {
    getChildFees(studentId).then(setData).catch(() => {});
  }, [studentId]);

  if (!data) return <Spinner />;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Due",  value: TZS(data.total_due),  color: "text-gray-700" },
          { label: "Total Paid", value: TZS(data.total_paid), color: "text-green-600" },
          { label: "Balance",    value: TZS(data.balance),    color: data.balance > 0 ? "text-red-600" : "text-green-600" },
        ].map(s => (
          <div key={s.label} className="rounded-xl border p-3 text-center" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
            <div className={`text-base font-bold ${s.color} tabular-nums`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {data.bills.length > 0 && (
        <Table
          headers={["Fee", "Year", "Term", "Due", "Paid", "Balance"]}
          rows={data.bills.map(b => [
            b.fee_name,
            b.year_label ?? "—",
            b.term,
            TZS(b.amount_due),
            TZS(b.amount_paid),
            <span className={b.balance > 0 ? "text-red-600" : "text-green-600"}>{TZS(b.balance)}</span>,
          ])}
        />
      )}

      {data.recent_payments.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Recent Payments</h4>
          <Table
            headers={["Date", "Amount", "Method", "Reference"]}
            rows={data.recent_payments.map(p => [
              p.payment_date, TZS(p.amount), p.payment_method, p.reference_no ?? "—",
            ])}
          />
        </div>
      )}
    </div>
  );
}

function AttendancePanel({ studentId }: { studentId: number }) {
  const [data, setData] = useState<AttendanceResponse | null>(null);

  useEffect(() => {
    getChildAttendance(studentId).then(setData).catch(() => {});
  }, [studentId]);

  if (!data) return <Spinner />;
  const { summary, records } = data;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Rate",    value: `${summary.rate}%`,  color: summary.rate >= 80 ? "text-green-600" : "text-red-600" },
          { label: "Present", value: summary.present,     color: "text-green-600" },
          { label: "Absent",  value: summary.absent,      color: "text-red-600" },
          { label: "Late",    value: summary.late,        color: "text-yellow-600" },
        ].map(s => (
          <div key={s.label} className="rounded-xl border p-3 text-center" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
            <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>
      {records.length === 0
        ? <Empty text="No records in the last 60 days." />
        : <Table
            headers={["Date", "Status"]}
            rows={records.map(r => [
              r.date,
              <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                r.status === "present" ? "bg-green-100 text-green-700" :
                r.status === "absent"  ? "bg-red-100 text-red-700" :
                "bg-yellow-100 text-yellow-700"
              }`}>{r.status}</span>,
            ])}
          />
      }
    </div>
  );
}

function LeavePanel({ studentId }: { studentId: number }) {
  const [requests, setRequests] = useState<LeaveRequest[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm]         = useState({ date_from: "", date_to: "", reason: "" });
  const [saving, setSaving]     = useState(false);
  const [err, setErr]           = useState("");

  const load = () => getChildLeave(studentId).then(setRequests).catch(() => setRequests([]));
  useEffect(() => { load(); }, [studentId]);

  const handleSubmit = async () => {
    if (!form.date_from || !form.date_to || !form.reason.trim()) {
      setErr("All fields are required."); return;
    }
    setSaving(true); setErr("");
    try {
      await submitLeave(studentId, form);
      setForm({ date_from: "", date_to: "", reason: "" });
      setShowForm(false);
      load();
    } catch { setErr("Failed to submit. Please try again."); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setShowForm(o => !o)}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition-colors"
        >
          <Plus size={14} /> Request Leave
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border p-4 space-y-3" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
          <h4 className="text-sm font-semibold">New Leave Request</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">From</label>
              <input type="date" value={form.date_from} onChange={e => setForm(f => ({ ...f, date_from: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">To</label>
              <input type="date" value={form.date_to} onChange={e => setForm(f => ({ ...f, date_to: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Reason</label>
            <textarea rows={3} value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none" style={{ borderColor: "var(--color-border)" }}
              placeholder="Explain the reason for absence…" />
          </div>
          {err && <p className="text-red-500 text-xs">{err}</p>}
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="text-sm px-3 py-1.5 rounded-lg border hover:bg-gray-50" style={{ borderColor: "var(--color-border)" }}>Cancel</button>
            <button onClick={handleSubmit} disabled={saving} className="text-sm px-3 py-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50">
              {saving ? "Submitting…" : "Submit"}
            </button>
          </div>
        </div>
      )}

      {!requests
        ? <Spinner />
        : requests.length === 0
          ? <Empty text="No leave requests yet." />
          : <Table
              headers={["From", "To", "Reason", "Status"]}
              rows={requests.map(r => [
                r.date_from, r.date_to,
                <span className="text-xs">{r.reason}</span>,
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  r.status === "approved" ? "bg-green-100 text-green-700" :
                  r.status === "rejected" ? "bg-red-100 text-red-700" :
                  "bg-yellow-100 text-yellow-700"
                }`}>{r.status}</span>,
              ])}
            />
      }
    </div>
  );
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────

function Spinner() {
  return <div className="flex justify-center py-8"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>;
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 text-center py-8">{text}</p>;
}

function Table({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 uppercase" style={{ background: "var(--color-surface-2)" }}>
            {headers.map(h => <th key={h} className="px-4 py-2">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "var(--color-border)" }}>
              {row.map((cell, j) => <td key={j} className="px-4 py-2.5">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ParentPortalPage() {
  const [children, setChildren]   = useState<PortalChild[] | null>(null);
  const [selected, setSelected]   = useState<number | null>(null);
  const [childTab, setChildTab]   = useState<ChildTab>("grades");
  const [error, setError]         = useState("");

  useEffect(() => {
    getParentChildren()
      .then(kids => {
        setChildren(kids);
        if (kids.length > 0) setSelected(kids[0].id);
      })
      .catch(() => setError("Failed to load children."));
  }, []);

  const childTabs: { key: ChildTab; label: string; icon: React.ReactNode }[] = [
    { key: "grades",     label: "Grades",     icon: <BookOpen size={14} /> },
    { key: "fees",       label: "Fees",       icon: <DollarSign size={14} /> },
    { key: "attendance", label: "Attendance", icon: <Calendar size={14} /> },
    { key: "leave",      label: "Leave",      icon: <FileText size={14} /> },
  ];

  if (!children) return <div className="flex justify-center py-16"><div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (error)     return <p className="text-red-500 text-sm text-center py-8">{error}</p>;
  if (children.length === 0) return (
    <div className="text-center py-16">
      <Users size={40} className="mx-auto text-gray-300 mb-3" />
      <p className="text-gray-500">No children linked to your account.</p>
      <p className="text-sm text-gray-400 mt-1">Contact the school administrator to link your children.</p>
    </div>
  );

  return (
    <div className="space-y-5">
      {/* Child selector */}
      {children.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {children.map(c => (
            <button
              key={c.id}
              onClick={() => { setSelected(c.id); setChildTab("grades"); }}
              className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                selected === c.id
                  ? "bg-violet-600 text-white border-violet-600"
                  : "border-gray-200 text-gray-600 hover:border-violet-300"
              }`}
            >
              {c.name}
              <span className="ml-1.5 text-xs opacity-70">{c.class_name ?? ""}</span>
            </button>
          ))}
        </div>
      )}

      {/* Selected child header */}
      {selected && (() => {
        const child = children.find(c => c.id === selected)!;
        return (
          <div className="rounded-2xl border p-4 flex items-center gap-4" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <div className="w-11 h-11 rounded-full bg-violet-100 flex items-center justify-center flex-shrink-0">
              <span className="text-violet-700 font-bold text-base">{child.name[0]}</span>
            </div>
            <div>
              <div className="font-semibold" style={{ color: "var(--color-on-surface)" }}>{child.name}</div>
              <div className="text-sm text-gray-500">{child.admission_no} · {child.class_name ?? "No class"} · {child.relation}</div>
            </div>
          </div>
        );
      })()}

      {/* Child tabs */}
      {selected && (
        <>
          <div className="flex gap-1 border-b" style={{ borderColor: "var(--color-border)" }}>
            {childTabs.map(t => (
              <button
                key={t.key}
                onClick={() => setChildTab(t.key)}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  childTab === t.key
                    ? "border-violet-600 text-violet-700"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.icon}{t.label}
              </button>
            ))}
          </div>

          <div key={`${selected}-${childTab}`}>
            {childTab === "grades"     && <GradesPanel     studentId={selected} />}
            {childTab === "fees"       && <FeesPanel       studentId={selected} />}
            {childTab === "attendance" && <AttendancePanel studentId={selected} />}
            {childTab === "leave"      && <LeavePanel      studentId={selected} />}
          </div>
        </>
      )}
    </div>
  );
}
