import { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { AlertTriangle, CheckCircle } from "lucide-react";
import Card from "@/components/ui/Card";
import Select from "@/components/ui/Select";
import SkeletonRow from "@/components/ui/SkeletonRow";
import {
  getMyClassInfo, getMyClassSubjectAverages, getMyClassTermComparison,
  getMyClassAttendanceTrend, getMyClassMissingMarks,
  type MyClassInfo, type SubjectAverage, type TermComparisonRow,
  type AttendanceTrendRow, type MissingMark,
} from "@/api/reports";

const GRADE_COLORS = { a: "#10b981", b: "#3b82f6", c: "#f59e0b", d: "#f97316", f: "#ef4444" };
const TERM_COLORS  = ["#7c3aed", "#0891b2", "#059669"];
const PIE_COLORS   = ["#10b981", "#3b82f6", "#f59e0b", "#f97316", "#ef4444"];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-700 mb-3">{children}</h3>;
}

export default function MyClassTab() {
  const [info, setInfo]           = useState<MyClassInfo | null>(null);
  const [examId, setExamId]       = useState<number | null>(null);
  const [averages, setAverages]   = useState<SubjectAverage[]>([]);
  const [comparison, setCompar]   = useState<TermComparisonRow[]>([]);
  const [trend, setTrend]         = useState<AttendanceTrendRow[]>([]);
  const [missing, setMissing]     = useState<MissingMark[]>([]);
  const [loading, setLoading]     = useState(true);
  const [noClass, setNoClass]     = useState(false);

  // Load class info + static data on mount
  useEffect(() => {
    Promise.all([getMyClassInfo(), getMyClassTermComparison(), getMyClassAttendanceTrend()])
      .then(([inf, comp, tr]) => {
        setInfo(inf);
        setCompar(comp);
        setTrend(tr);
        // Default exam: last published exam
        const published = inf.exams.filter((e) => e.status === "published");
        const last = published.length ? published[published.length - 1] : inf.exams[inf.exams.length - 1];
        if (last) setExamId(last.id);
      })
      .catch(() => setNoClass(true))
      .finally(() => setLoading(false));
  }, []);

  // Reload subject averages + missing marks when exam changes
  useEffect(() => {
    if (!info) return;
    Promise.all([
      getMyClassSubjectAverages(examId),
      getMyClassMissingMarks(examId),
    ]).then(([avgs, miss]) => {
      setAverages(avgs);
      setMissing(miss);
    });
  }, [examId, info]);

  // Aggregate grade distribution across all subjects for selected exam
  const gradeDist = averages.length
    ? [
        { name: "A", value: averages.reduce((s, r) => s + r.a, 0), color: GRADE_COLORS.a },
        { name: "B", value: averages.reduce((s, r) => s + r.b, 0), color: GRADE_COLORS.b },
        { name: "C", value: averages.reduce((s, r) => s + r.c, 0), color: GRADE_COLORS.c },
        { name: "D", value: averages.reduce((s, r) => s + r.d, 0), color: GRADE_COLORS.d },
        { name: "F", value: averages.reduce((s, r) => s + r.f, 0), color: PIE_COLORS[4] },
      ].filter((d) => d.value > 0)
    : [];

  const termsPresent = [...new Set(
    comparison.flatMap((r) => Object.keys(r).filter((k) => k.startsWith("term")))
  )].sort();

  if (loading) {
    return (
      <div className="space-y-3 mt-4">
        {Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={4} />)}
      </div>
    );
  }

  if (noClass || !info) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <AlertTriangle size={36} className="mb-3 opacity-40" />
        <p className="text-sm font-medium">No class assignment found.</p>
        <p className="text-xs mt-1">Ask an administrator to assign you as a class teacher.</p>
      </div>
    );
  }

  const examOptions = [
    { value: null as null, label: "All Exams" },
    ...info.exams.map((e) => ({ value: e.id, label: `${e.name} (Term ${e.term})` })),
  ];

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-gray-900">{info.class.name}</p>
          <p className="text-xs text-gray-500">{info.student_count} students enrolled</p>
        </div>
        <Select
          value={examId}
          onChange={(v) => setExamId(v as number | null)}
          options={examOptions}
          className="w-56"
        />
      </div>

      {/* Row 1: Subject averages bar + Grade distribution donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <SectionTitle>Subject Averages (%)</SectionTitle>
          {averages.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-10">No grade data for this exam.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={averages} margin={{ top: 4, right: 12, left: -10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="subject" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(v: any) => [`${v}%`, "Average"]} />
                <Bar dataKey="avg_pct" name="Average %" radius={[4, 4, 0, 0]}>
                  {averages.map((entry) => (
                    <Cell
                      key={entry.subject}
                      fill={entry.avg_pct >= 70 ? "#10b981" : entry.avg_pct >= 50 ? "#f59e0b" : "#ef4444"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <SectionTitle>Grade Distribution</SectionTitle>
          {gradeDist.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-10">No data.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={gradeDist} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                    dataKey="value" nameKey="name" paddingAngle={2}>
                    {gradeDist.map((d) => <Cell key={d.name} fill={d.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [v, "Students"]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2">
                {gradeDist.map((d) => (
                  <span key={d.name} className="flex items-center gap-1 text-xs text-gray-600">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: d.color }} />
                    {d.name}: {d.value}
                  </span>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Row 2: Term comparison grouped bar */}
      {comparison.length > 0 && termsPresent.length > 1 && (
        <Card>
          <SectionTitle>Term-by-Term Comparison (%)</SectionTitle>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={comparison} margin={{ top: 4, right: 12, left: -10, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="subject" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip formatter={(v: any) => [`${v ?? 0}%`]} />
              <Legend verticalAlign="top" height={28} />
              {termsPresent.map((tk, i) => (
                <Bar key={tk} dataKey={tk} name={`Term ${tk.replace("term", "")}`}
                  fill={TERM_COLORS[i] ?? "#6b7280"} radius={[3, 3, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Row 3: Attendance trend line chart */}
      <Card>
        <SectionTitle>Attendance Trend — Last 14 Weeks (%)</SectionTitle>
        {trend.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-10">No attendance data recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend} margin={{ top: 4, right: 12, left: -10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week_label" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip formatter={(v: any) => [`${v ?? 0}%`, "Attendance rate"]} />
              <Line type="monotone" dataKey="rate" stroke="#7c3aed" strokeWidth={2.5}
                dot={{ r: 4, fill: "#7c3aed" }} activeDot={{ r: 6 }} name="Rate %" />
              {/* 75% threshold line */}
              <Line dataKey={() => 75} stroke="#ef4444" strokeDasharray="5 3"
                strokeWidth={1.5} dot={false} name="Min. 75%" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Row 4: Missing marks */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <SectionTitle>
            <span className="flex items-center gap-2">
              {missing.length > 0
                ? <AlertTriangle size={14} className="text-amber-500" />
                : <CheckCircle size={14} className="text-emerald-500" />}
              Missing Marks
              {missing.length > 0 && (
                <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium ml-1">
                  {missing.length}
                </span>
              )}
            </span>
          </SectionTitle>
        </div>
        {missing.length === 0 ? (
          <p className="text-xs text-emerald-600 text-center py-6 font-medium">
            All grades are filled for this exam.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-amber-50 text-left text-xs font-medium text-amber-800 uppercase tracking-wide">
                  <th className="px-4 py-2.5">Student</th>
                  <th className="px-4 py-2.5">Adm. No</th>
                  <th className="px-4 py-2.5">Missing Subject</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {missing.map((m, i) => (
                  <tr key={i} className="hover:bg-amber-50/50">
                    <td className="px-4 py-2.5 font-medium text-gray-800">{m.student_name}</td>
                    <td className="px-4 py-2.5 text-gray-500">{m.admission_no}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">{m.subject}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
