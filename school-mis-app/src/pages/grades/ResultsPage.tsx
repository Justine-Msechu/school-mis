import { useState, useCallback } from "react";
import { Download, Printer, Search } from "lucide-react";
import { getExams, getClasses, getResultReport, type Exam, type ClassItem, type ResultReport } from "@/api/grades";
import { useEffect } from "react";
import Select from "@/components/ui/Select";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ResultsAnalytics from "@/components/grades/ResultsAnalytics";
import ResultsTable from "@/components/grades/ResultsTable";
import { downloadCSV, printHTML } from "@/utils/export";

export default function ResultsPage() {
  const [exams, setExams]     = useState<Exam[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [examId, setExamId]   = useState<number | null>(null);
  const [classId, setClassId] = useState<number | null>(null);
  const [report, setReport]   = useState<ResultReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [search, setSearch]   = useState("");

  useEffect(() => {
    getExams().then(setExams).catch(() => {});
    getClasses().then(setClasses).catch(() => {});
  }, []);

  const handleView = useCallback(async () => {
    if (!examId || !classId) return;
    setError("");
    setLoading(true);
    setReport(null);
    setSearch("");
    try {
      const r = await getResultReport(examId, classId);
      setReport(r);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to load results.");
    } finally {
      setLoading(false);
    }
  }, [examId, classId]);

  const handleExportCSV = () => {
    if (!report) return;
    const headers = [
      "Rank", "Student", "Adm No",
      ...report.subjects.map((s) => s.name),
      "Total", "Max", "Average %", "Grade",
    ];
    const rows = report.rows.map((r) => [
      r.rank,
      r.student_name,
      r.admission_no,
      ...report.subjects.map((s) => r.grades[s.id]?.score ?? ""),
      r.total,
      r.max_total,
      r.average != null ? r.average.toFixed(1) : "",
      r.overall_grade,
    ]);
    const examName = report.exam.name.replace(/\s+/g, "_");
    const className = report.class.name.replace(/\s+/g, "_");
    downloadCSV(`Results_${examName}_${className}`, headers, rows);
  };

  const handlePrint = () => {
    if (!report) return;
    const subjectHeaders = report.subjects.map((s) =>
      `<th class="center">${s.name}</th>`).join("");
    const tableRows = report.rows.map((r) => {
      const subjectCells = report.subjects.map((s) => {
        const g = r.grades[s.id];
        return `<td class="center">${g ? `${g.score} (${g.grade_letter})` : "—"}</td>`;
      }).join("");
      return `<tr>
        <td class="center bold">${r.rank}</td>
        <td>${r.student_name}</td>
        <td>${r.admission_no}</td>
        ${subjectCells}
        <td class="center bold">${r.total}/${r.max_total}</td>
        <td class="center bold">${r.average != null ? r.average.toFixed(1) + "%" : "—"}</td>
        <td class="center bold">${r.overall_grade}</td>
      </tr>`;
    }).join("");

    printHTML(
      `Results — ${report.exam.name} | ${report.class.name}`,
      `<h1>Results Report</h1>
       <h2>${report.exam.name} — ${report.class.name}</h2>
       <p class="meta">Generated: ${new Date().toLocaleString()} &nbsp;|&nbsp; ${report.rows.length} students</p>
       <div className="table-scroll"><table>
         <thead>
           <tr>
             <th class="center">#</th>
             <th>Student</th>
             <th>Adm No</th>
             ${subjectHeaders}
             <th class="center">Total</th>
             <th class="center">Avg %</th>
             <th class="center">Grade</th>
           </tr>
         </thead>
         <tbody>${tableRows}</tbody>
       </table></div>`,
    );
  };

  const examOptions   = exams.map((e) => ({ value: e.id, label: `${e.name} (T${e.term}) — ${e.year_label}` }));
  const classOptions  = classes.map((c) => ({ value: c.id, label: c.name }));
  const activeExam    = exams.find((e) => e.id === examId);
  const activeClass   = classes.find((c) => c.id === classId);

  return (
    <div className="page-content">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Results & Reports</h1>
        <p className="text-sm text-gray-500 mt-0.5">View and export academic performance reports by class and exam.</p>
      </div>

      <Card className="mb-5">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500">Exam</label>
            <Select
              value={examId}
              onChange={(v) => setExamId(v as number | null)}
              options={examOptions}
              placeholder="Select exam…"
              className="w-72"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500">Class</label>
            <Select
              value={classId}
              onChange={(v) => setClassId(v as number | null)}
              options={classOptions}
              placeholder="Select class…"
              className="w-48"
            />
          </div>
          <Button variant="primary" onClick={handleView} disabled={!examId || !classId} loading={loading}>
            View Results
          </Button>
        </div>

        {(activeExam || activeClass) && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
            <span className="text-2xs text-gray-400 font-medium">Viewing:</span>
            {activeExam && (
              <span className="status-chip bg-violet-50 text-violet-700 border border-violet-200">
                {activeExam.name}
              </span>
            )}
            {activeClass && (
              <span className="status-chip bg-blue-50 text-blue-700 border border-blue-200">
                {activeClass.name}
              </span>
            )}
            {report && (
              <span className="text-2xs text-gray-400 ml-2">
                {report.rows.length} students · {report.subjects.length} subjects
              </span>
            )}
          </div>
        )}
      </Card>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {report && <ResultsAnalytics report={report} />}

      {report && (
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search students…"
              className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" icon={<Download size={14} />} onClick={handleExportCSV}>
              Export CSV
            </Button>
            <Button variant="primary" size="sm" icon={<Printer size={14} />} onClick={handlePrint}>
              Print Report
            </Button>
          </div>
        </div>
      )}

      {(report || loading) && (
        <ResultsTable
          report={report ?? { exam: {} as Exam, class: {} as ClassItem, subjects: [], rows: [], school_type: "primary" }}
          loading={loading}
          search={search}
        />
      )}
    </div>
  );
}
