import { useState, useEffect, useCallback } from "react";
import { LayoutGrid, Plus, Edit2, Users, X } from "lucide-react";
import { getClassList, createClass, updateClass, getClassStudents, type ClassRecord, type ClassStudent } from "@/api/classes";
import { getTeachers, type Teacher } from "@/api/teachers";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ClassDialog({ initial, teachers, onSave, onClose }: {
  initial?: ClassRecord;
  teachers: Teacher[];
  onSave: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    name:        initial?.name        ?? "",
    grade_level: initial?.grade_level?.toString() ?? "",
    capacity:    initial?.capacity?.toString()    ?? "",
    room:        initial?.room        ?? "",
    teacher_id:  initial?.teacher_id?.toString()  ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) { setError("Class name is required."); return; }
    setSaving(true);
    setError("");
    try {
      const payload = {
        name:        form.name.trim(),
        grade_level: form.grade_level ? Number(form.grade_level) : null,
        capacity:    form.capacity    ? Number(form.capacity)    : null,
        room:        form.room        || null,
        teacher_id:  form.teacher_id  ? Number(form.teacher_id)  : null,
      };
      if (initial) {
        await updateClass(initial.id, payload);
      } else {
        await createClass(payload);
      }
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save class.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Class" : "Add Class"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Field label="Class Name *">
              <input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Grade 5A" />
            </Field>
          </div>
          <Field label="Grade Level">
            <input type="number" min="1" className={INPUT} value={form.grade_level} onChange={(e) => set("grade_level", e.target.value)} placeholder="e.g. 5" />
          </Field>
          <Field label="Capacity">
            <input type="number" min="1" className={INPUT} value={form.capacity} onChange={(e) => set("capacity", e.target.value)} placeholder="e.g. 40" />
          </Field>
          <Field label="Room">
            <input className={INPUT} value={form.room} onChange={(e) => set("room", e.target.value)} placeholder="e.g. Room 12" />
          </Field>
          <Field label="Class Teacher">
            <select className={INPUT} value={form.teacher_id} onChange={(e) => set("teacher_id", e.target.value)}>
              <option value="">— None —</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>{t.first_name} {t.last_name}</option>
              ))}
            </select>
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

function StudentsModal({ cls, onClose }: { cls: ClassRecord; onClose: () => void }) {
  const [students, setStudents] = useState<ClassStudent[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    getClassStudents(cls.id).then(setStudents).catch(() => {}).finally(() => setLoading(false));
  }, [cls.id]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">{cls.name} — Students</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-600 rounded"><X size={16} /></button>
        </div>
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="py-8 text-center text-sm text-gray-400">Loading…</div>
          ) : students.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">No students enrolled</div>
          ) : (
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase border-b border-gray-100">
                  <th className="pb-2">#</th>
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Adm. No</th>
                  <th className="pb-2">Gender</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {students.map((s, i) => (
                  <tr key={s.id}>
                    <td className="py-2 text-gray-400">{i + 1}</td>
                    <td className="py-2 font-medium text-gray-900">{s.first_name} {s.last_name}</td>
                    <td className="py-2 text-gray-500">{s.admission_no}</td>
                    <td className="py-2 text-gray-500">{s.gender === "M" ? "Male" : "Female"}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ClassesPage() {
  const { can } = useAuthStore();
  const [classes, setClasses]   = useState<ClassRecord[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading]   = useState(true);
  const [dialog, setDialog]     = useState<ClassRecord | null | "new">(null);
  const [viewing, setViewing]   = useState<ClassRecord | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getClassList().then(setClasses).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    getTeachers().then(setTeachers).catch(() => {});
  }, [load]);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Classes</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? "Loading…" : `${classes.length} classes`}
          </p>
        </div>
        {can("classes.manage") && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>Add Class</Button>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-32 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : classes.length === 0 ? (
        <EmptyState icon={LayoutGrid} title="No classes found" description="Add classes to get started." />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {classes.map((c) => (
            <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-shadow group">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-base font-bold text-gray-900 truncate">{c.name}</div>
                  {c.grade_level && <div className="text-xs text-gray-500 mt-0.5">Grade {c.grade_level}</div>}
                </div>
                {can("classes.manage") && (
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => setDialog(c)}
                      className="p-1 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded"
                    >
                      <Edit2 size={12} />
                    </button>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                <button
                  onClick={() => setViewing(c)}
                  className="flex items-center gap-1 text-xs text-violet-600 hover:text-violet-800 font-medium"
                >
                  <Users size={11} />
                  {c.student_count} student{c.student_count !== 1 ? "s" : ""}
                </button>
                {c.room && <span className="text-xs text-gray-400">{c.room}</span>}
              </div>

              {c.teacher_name && (
                <div className="mt-2 text-xs text-gray-500 truncate">
                  Teacher: {c.teacher_name}
                </div>
              )}
              {c.capacity && (
                <div className="mt-1">
                  <div className="w-full bg-gray-100 rounded-full h-1">
                    <div
                      className="bg-violet-500 h-1 rounded-full"
                      style={{ width: `${Math.min(100, (c.student_count / c.capacity) * 100)}%` }}
                    />
                  </div>
                  <div className="text-2xs text-gray-400 mt-0.5">{c.student_count}/{c.capacity} capacity</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {dialog !== null && (
        <ClassDialog
          initial={dialog === "new" ? undefined : dialog}
          teachers={teachers}
          onSave={() => { setDialog(null); load(); }}
          onClose={() => setDialog(null)}
        />
      )}
      {viewing && (
        <StudentsModal cls={viewing} onClose={() => setViewing(null)} />
      )}
    </div>
  );
}
