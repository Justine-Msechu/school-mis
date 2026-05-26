import { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { AlertTriangle, CheckCircle, BookOpen } from "lucide-react";
import Card from "@/components/ui/Card";
import Select from "@/components/ui/Select";
import SkeletonRow from "@/components/ui/SkeletonRow";
import {
  getMySubjectInfo, getMySubjectAverages, getMySubjectTermComparison,
  getMySubjectGradeDist, getMySubjectMissingMarks,
  type MySubjectInfo, type SubjectClassAverage, type SubjectTermRow,
  type GradeDist, type MissingMark,
} from "@/api/reports";

const GRADE_PIE_COLORS: Record<string, string> = {
  A: "#10b981", B: "#3b82f6", C: "#f59e0b", D: "#f97316", F: "#ef4444",
};
const TERM_COLORS = ["#7c3aed", "#0891b2", "#059669"];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-700 mb-3">{children}</h3>;
}

export default function MySubjectTab() {
  const [info, setInfo]           = useState<MySubjectInfo | null>(null);
  const [examId, setExamId]       = useState<number | null>(null);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [averages, setAverages]   = useState<SubjectClassAverage[]>([]);
  const [comparison, setCompar]   = useState<SubjectTermRow[]>([]);
  const [gradeDist, setGradeDist] = useState<GradeDist[]>([]);
  const [missing, setMissing]     = useState<MissingMark[]>([]);
  const [loading, setLoading]     = useState(true);
  const [noAssign, setNoAssign]   = useState(false);

  // Load info once on mount
  useEffect(() => {
    getMySubjectInfo()
      .then((inf) => {
        setInfo(inf);
        const last = inf.exams.filter((e) => e.status === "published");
        if (last.length) setExamId(last[last.length - 1].id);
        if (inf.subjects.length === 1) setSubjectId(inf.subjects[0].id);
      })
      .catch(() => setNoAssign(true))
      .finally(() => setLoading(false));
  }, []);

  // Reload charts when filters change
  useEffect(() => {
    if (!info) return;
    Promise.all([
      getMySubjectAverages(examId, subjectId),
      getMySubjectTermComparison(subjectId),
      getMySubjectGradeDist(examId, subjectId),
      getMySubjectMissingMarks(examId, subjectId),
    ]).then(([avgs, comp, dist, miss]) => {
      setAverages(avgs);
      setCompar(comp);
      setGradeDist(dist);
      setMissing(miss);
    });
  }, [examId, subjectId, info]);

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

  if (noAssign || !info) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <BookOpen size={36} className="mb-3 opacity-40" />
        <p className="text-sm font-medium">No subject assignments found.</p>
        <p className="text-xs mt-1">Ask an administrator to assign you to a class and subject.</p>
      </div>
    );
  }

  const examOptions = [
    { value: null as null, label: "All Exams" },
    ...info.exams.map((e) => ({ value: e.id, label: `${e.name} (Term ${e.term})` })),
  ];
  const subjectOptions = [
    { value: null as null, label: "All Subjects" },
    ...info.subjects.map((s) => ({ value: s.id, label: s.name })),
  ];

  // Bar chart label: "Subject – Class" or just "Class" if single subject
  const singleSubject = info.subjects.length === 1;
  const barLabel = (row: SubjectClassAverage) =>
    singleSubject ? row.class : `${row.subject} – ${row.class}`;

  const chartData = averages.map((r) => ({ ...r, label: barLabel(r) }));

  return (
    <div className="space-y-6">
      {/* Header + filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-gray-900">
            {info.subjects.map((s) => s.name).join(", ")}
          </p>
          <p className="text-xs text-gray-500">
            {info.assignments.map((a) => a.class_name).join(", ")}
          </p>
        </div>
        <div className="flex gap-2">
          {info.subjects.length > 1 && (
            <Select
              value={subjectId}
              onChange={(v) => setSubjectId(v as number | null)}
              options={subjectOptions}
              className="w-44"
            />
          )}
          <Select
            value={examId}
            onChange={(v) => setExamId(v as number | null)}
            options={examOptions}
            className="w-56"
          />
        </div>
      </div>

      {/* Row 1: Class averages bar + Grade distribution donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <SectionTitle>
            Class Performance — {singleSubject ? info.subjects[0].name : "Selected Subject"} (%)
          </SectionTitle>
          {chartData.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-10">No grade data for this selection.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 4, right: 12, left: -10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" interval={0} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip
                  formatter={(v: any, _name: any, props: any) => [
                    `${v}%`,
                    props.payload?.label,
                  ]}
                />
                <Bar dataKey="avg_pct" name="Average %" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry) => (
                    <Cell
                      key={entry.label}
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
                    {gradeDist.map((d) => (
                      <Cell key={d.name} fill={GRADE_PIE_COLORS[d.name] ?? "#6b7280"} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any) => [v, "Students"]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2">
                {gradeDist.map((d) => (
                  <span key={d.name} className="flex items-center gap-1 text-xs text-gray-600">
                    <span className="w-2.5 h-2.5 rounded-full inline-block"
                      style={{ background: GRADE_PIE_COLORS[d.name] ?? "#6b7280" }} />
                    {d.name}: {d.value}
                  </span>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Row 2: Term comparison */}
      {comparison.length > 0 && termsPresent.length > 1 && (
        <Card>
          <SectionTitle>Term-by-Term Comparison (%)</SectionTitle>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={comparison} margin={{ top: 4, right: 12, left: -10, bottom: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" interval={0} />
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

      {/* Row 3: Missing marks */}
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
            All marks entered for this exam.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-amber-50 text-left text-xs font-medium text-amber-800 uppercase tracking-wide">
                  <th className="px-4 py-2.5">Student</th>
                  <th className="px-4 py-2.5">Adm. No</th>
                  <th className="px-4 py-2.5">Subject</th>
                  <th className="px-4 py-2.5">Class</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {missing.map((m, i) => (
                  <tr key={i} className="hover:bg-amber-50/50">
                    <td className="px-4 py-2.5 font-medium text-gray-800">{m.student_name}</td>
                    <td className="px-4 py-2.5 text-gray-500">{m.admission_no}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded text-xs">{m.subject}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{m.class}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        )}
      </Card>
    </div>
  );
}
