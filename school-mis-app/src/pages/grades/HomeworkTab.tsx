import { useState, useEffect, useCallback, useRef } from "react";
import { Plus, BookOpen } from "lucide-react";
import api from "@/api/client";
import { getClasses, getSubjectsForClass, type ClassItem, type Subject } from "@/api/grades";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";
const TEXTAREA = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

interface Assignment {
  id: number;
  class_id: number;
  subject_id: number;
  title: string;
  instructions: string;
  deadline: string;
  max_points: number;
  class_name: string;
  subject_name: string;
}

function AssignmentDialog({ classes, onSave, onClose }: { classes: ClassItem[]; onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    class_id:     null as number | null,
    subject_id:   null as number | null,
    title:        "",
    instructions: "",
    deadline:     (() => { const d = new Date(); d.setDate(d.getDate() + 7); return d.toISOString().slice(0, 10); })(),
    max_points:   "100",
  });
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  useEffect(() => {
    if (form.class_id) {
      getSubjectsForClass(form.class_id).then(setSubjects).catch(() => setSubjects([]));
    } else {
      setSubjects([]);
    }
    setForm((f) => ({ ...f, subject_id: null }));
  }, [form.class_id]);

  const set = (k: string, v: string | number | null) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.class_id)   { setError("Please select a class."); return; }
    if (!form.subject_id) { setError("Please select a subject."); return; }
    if (!form.title)      { setError("Title is required."); return; }
    setSaving(true);
    setError("");
    try {
      await api.post("/grades/homework", {
        class_id:     form.class_id,
        subject_id:   form.subject_id,
        title:        form.title,
        instructions: form.instructions || "",
        deadline:     form.deadline,
        max_points:   Number(form.max_points) || 100,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to create assignment.");
    } finally {
      setSaving(false);
    }
  };

  const classOptions   = [{ value: null as null, label: "Select class…" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];
  const subjectOptions = [{ value: null as null, label: form.class_id ? "Select subject…" : "Select class first" }, ...subjects.map((s) => ({ value: s.id, label: s.name }))];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">New Assignment</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Class *">
            <Select value={form.class_id} onChange={(v) => set("class_id", v as number | null)} options={classOptions} />
          </Field>
          <Field label="Subject *">
            <Select
              value={form.subject_id}
              onChange={(v) => set("subject_id", v as number | null)}
              options={subjectOptions}
            />
          </Field>
          <Field label="Title *">
            <input className={INPUT} value={form.title} onChange={(e) => set("title", e.target.value)} />
          </Field>
          <Field label="Instructions">
            <textarea className={TEXTAREA} rows={3} value={form.instructions} onChange={(e) => set("instructions", e.target.value)} />
          </Field>
          <Field label="Deadline *">
            <input type="date" className={INPUT} value={form.deadline} onChange={(e) => set("deadline", e.target.value)} />
          </Field>
          <Field label="Max Points">
            <input type="number" min="1" className={INPUT} value={form.max_points} onChange={(e) => set("max_points", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Create"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function HomeworkTab() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [classes, setClasses]         = useState<ClassItem[]>([]);
  const [classId, setClassId]         = useState<number | null>(null);
  const [loading, setLoading]         = useState(true);
  const [dialog, setDialog]           = useState(false);
  const firstLoad = useRef(true);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    api.get("/grades/homework", { params: { class_id: classId } })
      .then((r) => { setAssignments(r.data); firstLoad.current = false; }).catch(() => {}).finally(() => setLoading(false));
  }, [classId]);

  useEffect(() => { getClasses().then(setClasses).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const classOptions = [{ value: null as null, label: "All Classes" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Homework</h2>
          <p className="text-sm text-gray-500 mt-0.5">Assignments and deadlines</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>New Assignment</Button>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <Select value={classId} onChange={(v) => setClassId(v as number | null)} options={classOptions} className="w-48" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Deadline</th>
              <th className="px-4 py-3">Max Points</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : assignments.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="py-16">
                    <EmptyState icon={BookOpen} title="No assignments" description="Homework assignments will appear here." />
                  </td>
                </tr>
              )
              : assignments.map((a) => {
                const isPast = new Date(a.deadline) < new Date();
                return (
                  <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{a.title}</td>
                    <td className="px-4 py-3 text-gray-600">{a.class_name}</td>
                    <td className="px-4 py-3 text-gray-600">{a.subject_name}</td>
                    <td className={`px-4 py-3 ${isPast ? "text-red-600 font-medium" : "text-gray-600"}`}>
                      {a.deadline}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.max_points}</td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>

      {dialog && (
        <AssignmentDialog
          classes={classes}
          onSave={() => { setDialog(false); load(); }}
          onClose={() => setDialog(false)}
        />
      )}
    </div>
  );
}
