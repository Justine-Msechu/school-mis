import { useState, useEffect, useCallback, useRef } from "react";
import { CalendarCheck, Save, CheckCircle, XCircle, CalendarDays } from "lucide-react";
import { getAttendanceSheet, saveAttendance, getAttendanceSummary, getLeaveRequests, reviewLeaveRequest, type AttendanceRow, type AttendanceSummaryDay } from "@/api/attendance";
import { getClassList, type ClassRecord } from "@/api/classes";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "mark" | "leave" | "summary";

const STATUS_OPTIONS = ["present", "absent", "late", "excused"];
const STATUS_COLOR: Record<string, string> = {
  present: "bg-emerald-100 text-emerald-700",
  absent:  "bg-red-100 text-red-700",
  late:    "bg-amber-100 text-amber-700",
  excused: "bg-blue-100 text-blue-700",
};

export default function AttendancePage() {
  const [tab, setTab]           = useState<Tab>("mark");
  const [classes, setClasses]   = useState<ClassRecord[]>([]);
  const [classId, setClassId]   = useState<number | null>(null);
  const [date, setDate]         = useState(new Date().toISOString().slice(0, 10));
  const [rows, setRows]         = useState<AttendanceRow[]>([]);
  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);

  // Leave requests
  const [leaveRequests, setLeaveRequests]   = useState<any[]>([]);
  const [leaveStatus, setLeaveStatus]       = useState("pending");
  const [leaveLoading, setLeaveLoading]     = useState(false);

  // Summary
  const [summaryRows, setSummaryRows]       = useState<AttendanceSummaryDay[]>([]);
  const [summaryDays, setSummaryDays]       = useState(30);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryClassId, setSummaryClassId] = useState<number | null>(null);

  // Track first loads per tab so skeleton only shows once
  const markLoaded    = useRef(false);
  const leaveLoaded   = useRef(false);
  const summaryLoaded = useRef(false);

  useEffect(() => {
    getClassList().then((cls) => {
      setClasses(cls);
      if (cls.length) setClassId(cls[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!classId || tab !== "mark") return;
    if (!markLoaded.current) setLoading(true);
    getAttendanceSheet(classId, date)
      .then((sheet) => { setRows(sheet.rows); markLoaded.current = true; })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [classId, date, tab]);

  useEffect(() => {
    if (tab !== "leave") return;
    if (!leaveLoaded.current) setLeaveLoading(true);
    getLeaveRequests(leaveStatus).then((d) => { setLeaveRequests(d); leaveLoaded.current = true; }).catch(() => {}).finally(() => setLeaveLoading(false));
  }, [tab, leaveStatus]);

  useEffect(() => {
    if (tab !== "summary") return;
    if (!summaryLoaded.current) setSummaryLoading(true);
    getAttendanceSummary(summaryClassId, summaryDays)
      .then((d) => { setSummaryRows(d); summaryLoaded.current = true; }).catch(() => {}).finally(() => setSummaryLoading(false));
  }, [tab, summaryClassId, summaryDays]);

  const setStatus = (id: number, status: string) =>
    setRows((prev) => prev.map((r) => r.id === id ? { ...r, status } : r));

  const handleSave = async () => {
    if (!classId) return;
    setSaving(true);
    try {
      await saveAttendance(classId, date, rows.map((r) => ({ student_id: r.id, status: r.status, remarks: r.remarks })));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {} finally { setSaving(false); }
  };

  const handleReview = async (id: number, status: string) => {
    await reviewLeaveRequest(id, status).catch(() => {});
    getLeaveRequests(leaveStatus).then(setLeaveRequests).catch(() => {});
  };

  const classOptions = [{ value: null as null, label: "Select class…" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];
  const summaryClassOptions = [{ value: null as null, label: "All Classes" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];
  const leaveStatusOptions = [{ value: "pending", label: "Pending" }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }];

  const TABS = [
    { key: "mark"    as Tab, label: "Mark Attendance" },
    { key: "leave"   as Tab, label: "Leave Requests" },
    { key: "summary" as Tab, label: "Summary" },
  ];

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Attendance</h1>
          <p className="text-sm text-gray-500 mt-0.5">Mark daily attendance by class</p>
        </div>
        {tab === "mark" && (
          <Button variant="primary" icon={<Save size={15} />} onClick={handleSave} disabled={saving || !rows.length}>
            {saved ? "Saved!" : saving ? "Saving…" : "Save"}
          </Button>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Mark Attendance */}
      {tab === "mark" && (
        <>
          <div className="flex items-center gap-3 mb-5 flex-wrap">
            <Select value={classId} onChange={(v) => setClassId(v as number | null)} options={classOptions} className="w-48" />
            <input
              type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
            {rows.length > 0 && (
              <span className="text-sm text-gray-500">
                {rows.filter((r) => r.status === "present").length} / {rows.length} present
              </span>
            )}
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3 w-8">#</th>
                  <th className="px-4 py-3">Student</th>
                  <th className="px-4 py-3">Adm. No</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  <tr><td colSpan={4} className="py-12 text-center text-gray-400 text-sm">Loading…</td></tr>
                ) : rows.length === 0 ? (
                  <tr><td colSpan={4} className="py-16"><EmptyState icon={CalendarCheck} title="No students" description="Select a class to mark attendance." /></td></tr>
                ) : (
                  rows.map((r, i) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 text-gray-400">{i + 1}</td>
                      <td className="px-4 py-2.5 font-medium text-gray-900">{r.first_name} {r.last_name}</td>
                      <td className="px-4 py-2.5 text-gray-500">{r.admission_no}</td>
                      <td className="px-4 py-2.5">
                        <div className="flex gap-1.5 flex-wrap">
                          {STATUS_OPTIONS.map((s) => (
                            <button key={s} onClick={() => setStatus(r.id, s)}
                              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors capitalize
                                ${r.status === s ? STATUS_COLOR[s] : "bg-gray-100 text-gray-500 hover:bg-gray-200"}`}>
                              {s}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table></div>
          </div>
        </>
      )}

      {/* Leave Requests */}
      {tab === "leave" && (
        <>
          <div className="flex items-center gap-3 mb-4">
            <Select value={leaveStatus} onChange={(v) => setLeaveStatus(v as string)} options={leaveStatusOptions} className="w-40" />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Student</th>
                  <th className="px-4 py-3">From</th>
                  <th className="px-4 py-3">To</th>
                  <th className="px-4 py-3">Reason</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {leaveLoading
                  ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                  : leaveRequests.length === 0
                  ? <tr><td colSpan={6} className="py-16"><EmptyState icon={CalendarCheck} title="No leave requests" /></td></tr>
                  : leaveRequests.map((lr) => (
                    <tr key={lr.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{lr.student_name}</div>
                        <div className="text-xs text-gray-400">{lr.admission_no}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{lr.date_from}</td>
                      <td className="px-4 py-3 text-gray-600">{lr.date_to}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{lr.reason || "—"}</td>
                      <td className="px-4 py-3">
                        {lr.status === "approved"
                          ? <Badge variant="green">Approved</Badge>
                          : lr.status === "rejected"
                          ? <Badge variant="red">Rejected</Badge>
                          : <Badge variant="amber">Pending</Badge>
                        }
                      </td>
                      <td className="px-4 py-3">
                        {lr.status === "pending" && (
                          <div className="flex gap-1">
                            <button
                              onClick={() => handleReview(lr.id, "approved")}
                              className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                              title="Approve"
                            >
                              <CheckCircle size={14} />
                            </button>
                            <button
                              onClick={() => handleReview(lr.id, "rejected")}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                              title="Reject"
                            >
                              <XCircle size={14} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table></div>
          </div>
        </>
      )}

      {/* Summary */}
      {tab === "summary" && (
        <>
          <div className="flex items-center gap-3 mb-4">
            <Select value={summaryClassId} onChange={(v) => setSummaryClassId(v as number | null)} options={summaryClassOptions} className="w-48" />
            <select
              value={summaryDays}
              onChange={(e) => setSummaryDays(Number(e.target.value))}
              className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Present</th>
                  <th className="px-4 py-3">Absent</th>
                  <th className="px-4 py-3">Late</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {summaryLoading
                  ? Array.from({ length: 7 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                  : summaryRows.length === 0
                  ? <tr><td colSpan={6} className="py-16"><EmptyState icon={CalendarDays} title="No attendance data" description="Mark attendance to see summary." /></td></tr>
                  : summaryRows.map((r) => {
                    const rate = r.total > 0 ? Math.round((r.present / r.total) * 100) : 0;
                    return (
                      <tr key={r.date} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 font-medium text-gray-900">{r.date}</td>
                        <td className="px-4 py-3 text-emerald-700 font-medium">{r.present}</td>
                        <td className="px-4 py-3 text-red-700">{r.absent}</td>
                        <td className="px-4 py-3 text-amber-700">{r.late}</td>
                        <td className="px-4 py-3 text-gray-600">{r.total}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-200 rounded-full h-1.5">
                              <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${rate}%` }} />
                            </div>
                            <span className={rate < 75 ? "text-red-600 font-medium text-xs" : "text-gray-600 text-xs"}>{rate}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                }
              </tbody>
            </table></div>
          </div>
        </>
      )}
    </div>
  );
}
