import { useState, useEffect, useRef } from "react";
import { BarChart3, Users, BookOpen, DollarSign, Activity, Download } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { getReportsOverview, getAttendanceSummaryReport, getGradeSummaryReport, type ReportsOverview, type AttendanceSummaryRow, type GradeSummaryRow } from "@/api/reports";
import { getExams } from "@/api/grades";
import StatCard from "@/components/ui/StatCard";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import { useAuthStore } from "@/stores/authStore";

type Tab = "overview" | "attendance" | "grades";

const fmt = (n: number) => `TZS ${(n ?? 0).toLocaleString()}`;

export default function ReportsPage() {
  const { can } = useAuthStore();
  const [tab, setTab]             = useState<Tab>("overview");
  const [overview, setOverview]   = useState<ReportsOverview | null>(null);
  const [attRows, setAttRows]     = useState<AttendanceSummaryRow[]>([]);
  const [gradeRows, setGradeRows] = useState<GradeSummaryRow[]>([]);
  const [exams, setExams]         = useState<{ id: number; name: string }[]>([]);
  const [examId, setExamId]       = useState<number | null>(null);
  const [loading, setLoading]     = useState(true);
  const attLoaded   = useRef(false);
  const gradesLoaded = useRef(false);

  useEffect(() => {
    Promise.all([getReportsOverview(), getExams()])
      .then(([ov, ex]: [ReportsOverview, { id: number; name: string }[]]) => { setOverview(ov); setExams(ex); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "attendance") {
      if (!attLoaded.current) setLoading(true);
      getAttendanceSummaryReport().then((d) => { setAttRows(d); attLoaded.current = true; }).catch(() => {}).finally(() => setLoading(false));
    } else if (tab === "grades") {
      if (!gradesLoaded.current) setLoading(true);
      getGradeSummaryReport(examId ?? undefined).then((d) => { setGradeRows(d); gradesLoaded.current = true; }).catch(() => {}).finally(() => setLoading(false));
    }
  }, [tab, examId]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview",   label: "Overview" },
    { key: "attendance", label: "Attendance" },
    { key: "grades",     label: "Grade Summary" },
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Reports</h1>
          <p className="text-sm text-gray-500 mt-0.5">School-wide analytics and summaries</p>
        </div>
        {tab === "attendance" && attRows.length > 0 && (
          <button
            onClick={() => downloadCSV("Attendance_Summary", ["Student","Adm No","Days","Present","Absent","Rate %"],
              attRows.map((r) => [r.student_name, r.admission_no, r.total_days, r.present, r.absent, r.rate]))}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download size={14} /> Export CSV
          </button>
        )}
        {tab === "grades" && gradeRows.length > 0 && (
          <button
            onClick={() => downloadCSV("Grade_Summary", ["Class","Subject","Students","Avg %","A","B","C","D","F"],
              gradeRows.map((r) => [r.class_name, r.subject_name, r.total, r.avg_pct ?? "", r.a_count, r.b_count, r.c_count, r.d_count, r.f_count]))}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download size={14} /> Export CSV
          </button>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && overview && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {overview.students    != null && <StatCard title="Students"       value={overview.students}            icon={Users}      color="#7C3AED" />}
          {overview.teachers    != null && <StatCard title="Teachers"       value={overview.teachers}            icon={Users}      color="#0891B2" />}
          {can("library.view") && overview.books        != null && <StatCard title="Library Books"  value={overview.books}           icon={BookOpen}   color="#059669" />}
          {can("library.view") && overview.active_loans != null && <StatCard title="Active Loans"   value={overview.active_loans}    icon={BookOpen}   color="#D97706" />}
          {(can("reports.finance") || can("finance.view")) && overview.total_revenue  != null && <StatCard title="Total Revenue"  value={fmt(overview.total_revenue)}  icon={DollarSign} color="#059669" />}
          {(can("reports.finance") || can("finance.view")) && overview.total_expenses != null && <StatCard title="Total Expenses" value={fmt(overview.total_expenses)} icon={DollarSign} color="#E11D48" />}
        </div>
      )}

      {tab === "attendance" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Adm. No</th>
                <th className="px-4 py-3">Days</th>
                <th className="px-4 py-3">Present</th>
                <th className="px-4 py-3">Absent</th>
                <th className="px-4 py-3">Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                : attRows.length === 0
                ? <tr><td colSpan={6} className="py-16"><EmptyState icon={Activity} title="No attendance data" /></td></tr>
                : attRows.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{r.student_name}</td>
                    <td className="px-4 py-3 text-gray-500">{r.admission_no}</td>
                    <td className="px-4 py-3 text-gray-600">{r.total_days}</td>
                    <td className="px-4 py-3 text-emerald-700">{r.present}</td>
                    <td className="px-4 py-3 text-red-700">{r.absent}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${r.rate}%` }} />
                        </div>
                        <span className={r.rate < 75 ? "text-red-600 font-medium" : "text-gray-700"}>{r.rate}%</span>
                      </div>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {tab === "grades" && (
        <>
          <div className="flex items-center gap-3 mb-4">
            <Select
              value={examId}
              onChange={(v) => setExamId(v as number | null)}
              options={[{ value: null as null, label: "All Exams" }, ...exams.map((e) => ({ value: e.id, label: e.name }))]}
              className="w-48"
            />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Students</th>
                  <th className="px-4 py-3">Avg %</th>
                  <th className="px-4 py-3">A</th>
                  <th className="px-4 py-3">B</th>
                  <th className="px-4 py-3">C</th>
                  <th className="px-4 py-3">D</th>
                  <th className="px-4 py-3">F</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={9} />)
                  : gradeRows.length === 0
                  ? <tr><td colSpan={9} className="py-16"><EmptyState icon={BarChart3} title="No grade data" /></td></tr>
                  : gradeRows.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{r.class_name}</td>
                      <td className="px-4 py-3 text-gray-600">{r.subject_name}</td>
                      <td className="px-4 py-3 text-gray-600">{r.total}</td>
                      <td className="px-4 py-3 font-medium">{r.avg_pct ?? "—"}%</td>
                      <td className="px-4 py-3 text-emerald-700">{r.a_count}</td>
                      <td className="px-4 py-3 text-cyan-700">{r.b_count}</td>
                      <td className="px-4 py-3 text-amber-700">{r.c_count}</td>
                      <td className="px-4 py-3 text-orange-700">{r.d_count}</td>
                      <td className="px-4 py-3 text-red-700">{r.f_count}</td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
