import { useState, useEffect, useRef } from "react";
import { Lock } from "lucide-react";
import {
  getExams, getClasses, getSubjectsForClass, getGradeSheet,
  saveGrades, submitGrades, requestGradeChange,
  type Exam, type ClassItem, type Subject, type GradeRow,
} from "@/api/grades";
import Select from "@/components/ui/Select";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import GradeBadge from "@/components/ui/GradeBadge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import StickyContextBar from "@/components/grades/StickyContextBar";
import { useAuthStore } from "@/stores/authStore";

const GRADE_LETTER_MAP: Record<string, [number, number]> = {
  A: [80, 100], B: [65, 79], C: [50, 64], D: [40, 49], F: [0, 39],
};

function computeLetter(score: number, max: number): string {
  const pct = max > 0 ? (score / max) * 100 : 0;
  if (pct >= 80) return "A";
  if (pct >= 65) return "B";
  if (pct >= 50) return "C";
  if (pct >= 40) return "D";
  return "F";
}

type LocalRow = GradeRow & { _score: number; _max: number; _remarks: string; _letter: string };

function toLocalRow(r: GradeRow): LocalRow {
  const score = r.score ?? 0;
  const max = r.max_score ?? 100;
  return {
    ...r,
    _score: score,
    _max: max,
    _remarks: r.remarks ?? "",
    _letter: r.grade_letter ?? computeLetter(score, max),
  };
}

export default function GradeEntryPage() {
  const { can } = useAuthStore();

  const [exams, setExams]       = useState<Exam[]>([]);
  const [classes, setClasses]   = useState<ClassItem[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  const [examId, setExamId]       = useState<number | null>(null);
  const [classId, setClassId]     = useState<number | null>(null);
  const [subjectId, setSubjectId] = useState<number | null>(null);

  const [rows, setRows]     = useState<LocalRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving]   = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loaded, setLoaded]   = useState(false);

  // Change request modal state
  const [changeTarget, setChangeTarget] = useState<LocalRow | null>(null);
  const [changePw, setChangePw]         = useState({ score: 0, max: 100, reason: "" });

  useEffect(() => {
    getExams().then(setExams).catch(() => {});
    getClasses().then(setClasses).catch(() => {});
  }, []);

  useEffect(() => {
    setSubjectId(null);
    setSubjects([]);
    if (!classId) return;
    getSubjectsForClass(classId).then(setSubjects).catch(() => {});
  }, [classId]);

  const handleLoad = async () => {
    if (!examId || !classId || !subjectId) return;
    setLoading(true);
    setLoaded(false);
    try {
      const sheet = await getGradeSheet(examId, classId, subjectId);
      setRows(sheet.map(toLocalRow));
      setLoaded(true);
    } catch { /* toast */ }
    finally { setLoading(false); }
  };

  const updateRow = (idx: number, patch: Partial<LocalRow>) => {
    setRows((prev) => {
      const next = [...prev];
      const merged = { ...next[idx], ...patch };
      if (patch._score !== undefined || patch._max !== undefined) {
        merged._letter = computeLetter(merged._score, merged._max);
      }
      next[idx] = merged;
      return next;
    });
  };

  const collectEditable = () =>
    rows
      .filter((r) => !["submitted_locked", "approved"].includes(r.status))
      .map((r) => ({ student_id: r.student_id, score: r._score, max_score: r._max, remarks: r._remarks }));

  const handleSave = async () => {
    if (!examId || !classId || !subjectId) return;
    setSaving(true);
    try {
      await saveGrades(examId, classId, subjectId, collectEditable());
      await handleLoad();
    } catch { /* toast */ }
    finally { setSaving(false); }
  };

  const handleSubmit = async () => {
    if (!examId || !classId || !subjectId) return;
    if (!confirm("Finalize & submit these grades? Submitted grades are locked for further changes except via a formal change request.")) return;
    setSubmitting(true);
    try {
      await saveGrades(examId, classId, subjectId, collectEditable());
      await submitGrades(examId, classId, subjectId);
      await handleLoad();
    } catch { /* toast */ }
    finally { setSubmitting(false); }
  };

  const handleChangeRequest = async () => {
    if (!changeTarget) return;
    try {
      await requestGradeChange(changeTarget.grade_id!, changePw.score, changePw.max, changePw.reason);
      setChangeTarget(null);
    } catch { /* toast */ }
  };

  const counts = {
    draft:    rows.filter((r) => r.status === "draft").length,
    locked:   rows.filter((r) => r.status === "submitted_locked").length,
    approved: rows.filter((r) => r.status === "approved").length,
    empty:    rows.filter((r) => !r.status || r.status === "not_entered").length,
    total:    rows.length,
  };
  const hasEditable = rows.some((r) => !["submitted_locked", "approved"].includes(r.status));

  const examLabel    = exams.find((e) => e.id === examId)?.name ?? "—";
  const classLabel   = classes.find((c) => c.id === classId)?.name ?? "—";
  const subjectLabel = subjects.find((s) => s.id === subjectId)?.name ?? "—";

  const examOptions    = exams.map((e) => ({ value: e.id, label: `${e.name} (T${e.term}) [${e.status}]` }));
  const classOptions   = classes.map((c) => ({ value: c.id, label: c.name }));
  const subjectOptions = subjects.map((s) => ({ value: s.id, label: s.name }));

  return (
    <div className="flex flex-col min-h-full">
      {/* Sticky context bar — visible once a sheet is loaded */}
      {loaded && (
        <StickyContextBar
          examLabel={examLabel}
          classLabel={classLabel}
          subjectLabel={subjectLabel}
          status={counts}
          hasEditable={hasEditable}
          saving={saving}
          submitting={submitting}
          onSave={handleSave}
          onSubmit={handleSubmit}
        />
      )}

      <div className="p-8 max-w-screen-xl mx-auto w-full">
        {!loaded && (
          <>
            <div className="mb-6">
              <h1 className="text-xl font-bold text-gray-900">Grade Entry</h1>
              <p className="text-sm text-gray-500 mt-0.5">Select an exam, class, and subject to load the grade sheet.</p>
            </div>

            {/* Open exams banner */}
            {exams.filter((e) => e.status === "open").length > 0 && (
              <div className="mb-5 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <p className="text-xs font-semibold text-emerald-700 mb-2">Open for grade entry:</p>
                <div className="flex flex-wrap gap-2">
                  {exams.filter((e) => e.status === "open").map((e) => (
                    <button
                      key={e.id}
                      onClick={() => setExamId(e.id)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                        examId === e.id
                          ? "bg-emerald-600 text-white border-emerald-600"
                          : "bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-100"
                      }`}
                    >
                      {e.name} {e.term ? `(T${e.term})` : ""}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Selector card */}
            <Card className="mb-6">
              <div className="flex items-end gap-3 flex-wrap">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-500">Exam</label>
                  <Select value={examId} onChange={(v) => setExamId(v as number | null)} options={examOptions} placeholder="Select exam…" className="w-64" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-500">Class</label>
                  <Select value={classId} onChange={(v) => setClassId(v as number | null)} options={classOptions} placeholder="Select class…" className="w-40" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-500">Subject</label>
                  <Select value={subjectId} onChange={(v) => setSubjectId(v as number | null)} options={subjectOptions} placeholder="Select subject…" className="w-44" disabled={!classId} />
                </div>
                <Button variant="primary" onClick={handleLoad} disabled={!examId || !classId || !subjectId} loading={loading}>
                  Load Sheet
                </Button>
              </div>
            </Card>
          </>
        )}

        {/* Entry table */}
        {(loaded || loading) && (
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 w-[200px]">Student</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 w-24">Adm No</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 w-28">Score</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 w-24">/ Max</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 w-20">Grade</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Remarks</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 w-28">Status</th>
                  <th className="px-4 py-3 w-32" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={8} />)
                  : rows.map((row, idx) => {
                      const locked = ["submitted_locked", "approved"].includes(row.status);
                      const statusColors: Record<string, string> = {
                        draft:            "bg-amber-100 text-amber-700",
                        submitted_locked: "bg-blue-100 text-blue-700",
                        approved:         "bg-emerald-100 text-emerald-700",
                      };
                      return (
                        <tr key={row.student_id} className={locked ? "bg-gray-50/50" : "hover:bg-gray-50/70"}>
                          <td className="px-4 py-2.5 font-medium text-gray-900">{row.student_name}</td>
                          <td className="px-4 py-2.5 text-gray-500 text-xs">{row.admission_no}</td>

                          {/* Score input */}
                          <td className="px-4 py-2.5 text-center">
                            {locked ? (
                              <span className="text-gray-400 text-xs">{row.score ?? "—"}</span>
                            ) : (
                              <input
                                type="number"
                                min={0}
                                max={row._max}
                                step={0.5}
                                value={row._score}
                                onChange={(e) => updateRow(idx, { _score: parseFloat(e.target.value) || 0 })}
                                className="w-20 h-8 text-center border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                              />
                            )}
                          </td>

                          {/* Max input */}
                          <td className="px-4 py-2.5 text-center">
                            {locked ? (
                              <span className="text-gray-400 text-xs">{row.max_score}</span>
                            ) : (
                              <input
                                type="number"
                                min={1}
                                step={1}
                                value={row._max}
                                onChange={(e) => updateRow(idx, { _max: parseFloat(e.target.value) || 100 })}
                                className="w-16 h-8 text-center border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                              />
                            )}
                          </td>

                          {/* Live grade badge */}
                          <td className="px-4 py-2.5 text-center">
                            <GradeBadge letter={row._letter || "—"} />
                          </td>

                          {/* Remarks */}
                          <td className="px-4 py-2.5">
                            {locked ? (
                              <span className="text-gray-400 text-xs">{row.remarks || "—"}</span>
                            ) : (
                              <input
                                type="text"
                                value={row._remarks}
                                onChange={(e) => updateRow(idx, { _remarks: e.target.value })}
                                placeholder="Optional remarks…"
                                className="w-full h-8 px-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-violet-400"
                              />
                            )}
                          </td>

                          {/* Status badge */}
                          <td className="px-4 py-2.5 text-center">
                            <span className={`status-chip ${statusColors[row.status] ?? "bg-gray-100 text-gray-500"}`}>
                              {locked && <Lock size={9} />}
                              {row.status === "draft" && "Draft"}
                              {row.status === "submitted_locked" && "Locked"}
                              {row.status === "approved" && "Approved"}
                              {!row.status || row.status === "not_entered" ? "Not entered" : ""}
                            </span>
                          </td>

                          {/* Actions */}
                          <td className="px-4 py-2.5 text-right">
                            {locked && row.grade_id && can("grades.change_request.create") && (
                              <button
                                onClick={() => {
                                  setChangeTarget(row);
                                  setChangePw({ score: row.score ?? 0, max: row.max_score ?? 100, reason: "" });
                                }}
                                className="text-2xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 hover:bg-amber-100"
                              >
                                Request Change ↗
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>

            {loaded && rows.length === 0 && (
              <EmptyState title="No students in this class" description="The selected class has no active students." />
            )}
          </div>
        )}

        {/* Change request modal */}
        {changeTarget && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
              <h3 className="text-base font-bold text-gray-900 mb-1">Request Grade Change</h3>
              <p className="text-xs text-gray-500 mb-4">For: <strong>{changeTarget.student_name}</strong></p>

              <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                This grade is locked. Submitting a request will send it to an academic officer for review.
              </div>

              <div className="space-y-3">
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="block text-xs font-semibold text-gray-500 mb-1">Proposed Score</label>
                    <input type="number" value={changePw.score} onChange={(e) => setChangePw((p) => ({ ...p, score: +e.target.value }))}
                      className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-semibold text-gray-500 mb-1">Out of (Max)</label>
                    <input type="number" value={changePw.max} onChange={(e) => setChangePw((p) => ({ ...p, max: +e.target.value }))}
                      className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1">Reason (required)</label>
                  <textarea value={changePw.reason} onChange={(e) => setChangePw((p) => ({ ...p, reason: e.target.value }))}
                    rows={3} placeholder="Explain the reason for this change…"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-violet-500" />
                </div>
              </div>

              <div className="flex gap-2 justify-end mt-5">
                <Button variant="outline" onClick={() => setChangeTarget(null)}>Cancel</Button>
                <Button variant="warning" onClick={handleChangeRequest} disabled={!changePw.reason.trim()}>
                  Submit Request
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
