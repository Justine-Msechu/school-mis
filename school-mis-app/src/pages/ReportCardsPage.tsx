import { useEffect, useRef, useState } from "react";
import { FileText, Printer } from "lucide-react";
import { printHTML } from "@/utils/export";
import PageHeader from "@/components/ui/PageHeader";
import Modal from "@/components/ui/Modal";
import FormField from "@/components/ui/FormField";
import { DataTable, type Column } from "@/components/data/DataTable";
import { useToast } from "@/components/ui/Toast";
import { generateCards, listCards, publishCard, lockCard, type ReportCard } from "@/api/reportCards";
import api from "@/api/client";

interface Exam { id: number; name: string; }
interface ClassRow { id: number; name: string; }

export default function ReportCardsPage() {
  const toast = useToast();
  const firstLoad = useRef(true);
  const [loading, setLoading] = useState(false);
  const [exams, setExams] = useState<Exam[]>([]);
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [exam, setExam] = useState<number | "">("");
  const [classId, setClassId] = useState<number | "">("");
  const [cards, setCards] = useState<ReportCard[]>([]);
  const [selected, setSelected] = useState<ReportCard | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [genOpen, setGenOpen] = useState(false);
  const [genExam, setGenExam] = useState<number | "">("");
  const [genClass, setGenClass] = useState<number | "">("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/grades/exams").then((r) => r.data),
      api.get("/classes").then((r) => r.data),
    ]).then(([ex, cls]) => {
      setExams(ex.items || ex);
      setClasses(cls.items || cls);
    });
  }, []);

  const loadCards = (examId: number, clsId?: number) => {
    setLoading(true);
    listCards(examId, clsId || undefined)
      .then(setCards)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!exam) { setCards([]); return; }
    loadCards(exam as number, classId as number || undefined);
  }, [exam, classId]);

  const handleGenerate = async () => {
    if (!genExam || !genClass) return;
    setGenerating(true);
    try {
      const result = await generateCards(genExam as number, genClass as number);
      toast.success(`Generated ${result.created} cards for ${result.class}`);
      setGenOpen(false);
      if (exam) loadCards(exam as number, classId as number || undefined);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async (card: ReportCard) => {
    try {
      await publishCard(card.id);
      toast.success("Card published");
      if (exam) loadCards(exam as number, classId as number || undefined);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to publish");
    }
  };

  const handlePrint = (card: ReportCard) => {
    const subjectRows = (card.subjects ?? []).map((s) => `
      <tr>
        <td>${s.subject_name}</td>
        <td class="center">${s.marks_obtained ?? "—"}/${s.total_marks ?? "—"}</td>
        <td class="center">${s.percentage != null ? s.percentage.toFixed(1) + "%" : "—"}</td>
        <td class="center bold">${s.grade_label ?? "—"}</td>
      </tr>`).join("");

    printHTML(
      `Report Card — ${card.student_name}`,
      `<h1>Student Report Card</h1>
       <h2>${card.class_name_snapshot ?? ""}</h2>
       <p class="meta">
         <strong>Name:</strong> ${card.student_name} &nbsp;|&nbsp;
         <strong>Adm No:</strong> ${card.admission_no} &nbsp;|&nbsp;
         <strong>Rank:</strong> #${card.class_rank ?? "—"} &nbsp;|&nbsp;
         <strong>Overall:</strong> ${card.overall_pct != null ? card.overall_pct.toFixed(1) + "%" : "—"} — Grade ${card.overall_grade ?? "—"}
       </p>
       <div className="table-scroll"><table>
         <thead>
           <tr>
             <th>Subject</th>
             <th class="center">Marks</th>
             <th class="center">%</th>
             <th class="center">Grade</th>
           </tr>
         </thead>
         <tbody>${subjectRows}</tbody>
       </table></div>`,
    );
  };

  const handleLock = async (card: ReportCard) => {
    try {
      await lockCard(card.id);
      toast.success("Card locked");
      if (exam) loadCards(exam as number, classId as number || undefined);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to lock");
    }
  };

  const columns: Column<ReportCard>[] = [
    { key: "class_rank", header: "#", sortable: true, render: (row) => <span className="font-bold text-gray-500">{row.class_rank ?? "—"}</span> },
    { key: "student_name", header: "Student", sortable: true },
    { key: "admission_no", header: "Adm No", sortable: true },
    { key: "overall_pct", header: "Score %", sortable: true, render: (row) => row.overall_pct != null ? (
      <span className={`font-semibold ${row.overall_pct >= 75 ? "text-green-600" : row.overall_pct >= 50 ? "text-yellow-600" : "text-red-600"}`}>
        {row.overall_pct.toFixed(1)}%
      </span>
    ) : <span>—</span> },
    { key: "overall_grade", header: "Grade", sortable: true, render: (row) => row.overall_grade ? (
      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-bold">{row.overall_grade}</span>
    ) : <span>—</span> },
    { key: "is_published", header: "Status", render: (row) => (
      row.is_locked ? <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs">Locked</span> :
      row.is_published ? <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">Published</span> :
      <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full text-xs">Draft</span>
    )},
    { key: "id", header: "", render: (row) => (
      <div className="flex gap-1">
        <button onClick={(e) => { e.stopPropagation(); setSelected(row); setDetailOpen(true); }}
          className="px-2 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50">View</button>
        {!row.is_published && !row.is_locked && (
          <button onClick={(e) => { e.stopPropagation(); handlePublish(row); }}
            className="px-2 py-1 text-xs border border-green-200 text-green-600 rounded hover:bg-green-50">Publish</button>
        )}
        {row.is_published && !row.is_locked && (
          <button onClick={(e) => { e.stopPropagation(); handleLock(row); }}
            className="px-2 py-1 text-xs border border-gray-200 text-gray-600 rounded hover:bg-gray-50">Lock</button>
        )}
      </div>
    )},
  ];

  return (
    <div className="p-6">
      <PageHeader
        title="Report Cards"
        subtitle="Generate and manage student report cards"
        actions={
          <button onClick={() => setGenOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition-colors">
            <FileText size={15} /> Generate Cards
          </button>
        }
      />

      <div className="flex gap-3 mb-6">
        <select value={exam} onChange={(e) => setExam(Number(e.target.value))}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
          <option value="">Select exam</option>
          {exams.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
        <select value={classId} onChange={(e) => setClassId(Number(e.target.value) || "")}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
          <option value="">All classes</option>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <DataTable<ReportCard>
          columns={columns}
          rows={cards}
          loading={loading}
          emptyTitle="Select an exam to view report cards"
        />
      </div>

      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title="Report Card" size="lg">
        {selected && (
          <div>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lg">{selected.student_name}</h3>
                <p className="text-sm text-gray-500">{selected.class_name_snapshot} · Rank #{selected.class_rank}</p>
                <button
                  onClick={() => handlePrint(selected)}
                  className="mt-2 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Printer size={12} /> Print
                </button>
              </div>
              <div className="text-right">
                <div className={`text-2xl font-bold ${
                  (selected.overall_pct ?? 0) >= 75 ? "text-green-600" :
                  (selected.overall_pct ?? 0) >= 50 ? "text-yellow-600" : "text-red-600"
                }`}>{selected.overall_pct?.toFixed(1) ?? "—"}%</div>
                <div className="text-sm text-gray-500">Grade: {selected.overall_grade ?? "—"}</div>
              </div>
            </div>
            {selected.subjects && selected.subjects.length > 0 && (
              <div className="table-scroll"><table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2 text-xs font-semibold text-gray-500">Subject</th>
                    <th className="text-right py-2 text-xs font-semibold text-gray-500">Marks</th>
                    <th className="text-right py-2 text-xs font-semibold text-gray-500">%</th>
                    <th className="text-right py-2 text-xs font-semibold text-gray-500">Grade</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.subjects.map((s) => (
                    <tr key={s.id} className="border-b border-gray-50">
                      <td className="py-2 text-gray-700">{s.subject_name}</td>
                      <td className="py-2 text-right text-gray-600">{s.marks_obtained ?? "—"}/{s.total_marks ?? "—"}</td>
                      <td className="py-2 text-right text-gray-600">{s.percentage?.toFixed(1) ?? "—"}%</td>
                      <td className="py-2 text-right">
                        <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-bold">{s.grade_label ?? "—"}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </div>
        )}
      </Modal>

      <Modal open={genOpen} onClose={() => setGenOpen(false)} title="Generate Report Cards"
        footer={
          <>
            <button onClick={() => setGenOpen(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
            <button onClick={handleGenerate} disabled={generating || !genExam || !genClass}
              className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {generating ? "Generating…" : "Generate"}
            </button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">Generates report cards from grades already entered for the selected exam and class.</p>
          <FormField label="Exam" required>
            <select value={genExam} onChange={(e) => setGenExam(Number(e.target.value))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none w-full">
              <option value="">Select exam</option>
              {exams.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </FormField>
          <FormField label="Class" required>
            <select value={genClass} onChange={(e) => setGenClass(Number(e.target.value))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none w-full">
              <option value="">Select class</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </FormField>
        </div>
      </Modal>
    </div>
  );
}
