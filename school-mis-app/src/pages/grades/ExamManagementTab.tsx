import { useState, useEffect } from "react";
import { Plus, Edit2 } from "lucide-react";
import { getExams, type Exam } from "@/api/grades";
import api from "@/api/client";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const STATUS_VARIANT: Record<string, string> = {
  open:    "green",
  closed:  "red",
  draft:   "gray",
};

interface ExamFormProps {
  initial?: Exam;
  onSave: (data: { name: string; term: number; year_label: string; status: string }) => void;
  onCancel: () => void;
}

function ExamForm({ initial, onSave, onCancel }: ExamFormProps) {
  const [name, setName]       = useState(initial?.name || "");
  const [term, setTerm]       = useState(initial?.term ?? 1);
  const [year, setYear]       = useState(initial?.year_label || new Date().getFullYear().toString());
  const [status, setStatus]   = useState(initial?.status || "open");
  const [saving, setSaving]   = useState(false);

  const submit = async () => {
    setSaving(true);
    try { await onSave({ name, term, year_label: year, status }); } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Exam" : "New Exam"}</h2>
        <div className="flex flex-col gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Term</label>
              <select value={term} onChange={(e) => setTerm(Number(e.target.value))}
                className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                {[1, 2, 3].map((t) => <option key={t} value={t}>Term {t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Year</label>
              <input value={year} onChange={(e) => setYear(e.target.value)}
                className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}
              className="w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving || !name}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function ExamManagementTab() {
  const [exams, setExams]     = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Exam | null | "new">(null);

  const load = () => {
    setLoading(true);
    getExams().then(setExams).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (data: any) => {
    if (editing === "new") {
      await api.post("/grades/exams", data);
    } else if (editing) {
      await api.put(`/grades/exams/${editing.id}`, data);
    }
    setEditing(null);
    load();
  };

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Exam Management</h2>
          <p className="text-sm text-gray-500 mt-0.5">Create and manage exams</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setEditing("new")}>New Exam</Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Term</th>
              <th className="px-4 py-3">Year</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : exams.length === 0
              ? <tr><td colSpan={5} className="py-16"><EmptyState icon={Plus} title="No exams yet" /></td></tr>
              : exams.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.name}</td>
                  <td className="px-4 py-3 text-gray-600">Term {e.term}</td>
                  <td className="px-4 py-3 text-gray-600">{e.year_label}</td>
                  <td className="px-4 py-3">
                    <Badge variant={(STATUS_VARIANT[e.status] || "gray") as any}>{e.status}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setEditing(e)}
                      className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors"
                    >
                      <Edit2 size={14} />
                    </button>
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>

      {editing !== null && (
        <ExamForm
          initial={editing === "new" ? undefined : editing}
          onSave={handleSave}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
}
