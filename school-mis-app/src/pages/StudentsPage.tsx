import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Plus, Edit2, UserX } from "lucide-react";
import { getStudents, createStudent, updateStudent, deactivateStudent, type Student, type StudentList } from "@/api/students";
import { getClasses, type ClassItem } from "@/api/grades";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import { Users } from "lucide-react";

const PAGE_SIZE = 30;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

interface StudentDialogProps {
  classes: ClassItem[];
  initial?: Student;
  onSave: () => void;
  onClose: () => void;
}

function StudentDialog({ classes, initial, onSave, onClose }: StudentDialogProps) {
  const [form, setForm] = useState({
    first_name:     initial?.first_name     ?? "",
    last_name:      initial?.last_name      ?? "",
    admission_no:   initial?.admission_no   ?? "",
    gender:         initial?.gender         ?? "M",
    class_id:       initial?.class_id       ?? null as number | null,
    date_of_birth:  initial?.date_of_birth  ?? "",
    guardian_name:  initial?.guardian_name  ?? "",
    guardian_phone: initial?.guardian_phone ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.first_name || !form.last_name || !form.admission_no) {
      setError("First name, last name and admission number are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (initial) {
        await updateStudent(initial.id, form);
      } else {
        await createStudent(form);
      }
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save student.");
    } finally {
      setSaving(false);
    }
  };

  const classOptions = [
    { value: null as null, label: "No class" },
    ...classes.map((c) => ({ value: c.id, label: c.name })),
  ];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Student" : "Add Student"}</h2>

        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

        <div className="grid grid-cols-2 gap-3">
          <Field label="First Name *">
            <input className={INPUT} value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
          </Field>
          <Field label="Last Name *">
            <input className={INPUT} value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
          </Field>
          <Field label="Admission No *">
            <input className={INPUT} value={form.admission_no} onChange={(e) => set("admission_no", e.target.value)} />
          </Field>
          <Field label="Gender">
            <select className={INPUT} value={form.gender} onChange={(e) => set("gender", e.target.value)}>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </Field>
          <Field label="Class">
            <Select value={form.class_id} onChange={(v) => set("class_id", v as number | null)} options={classOptions} />
          </Field>
          <Field label="Date of Birth">
            <input type="date" className={INPUT} value={form.date_of_birth ?? ""} onChange={(e) => set("date_of_birth", e.target.value)} />
          </Field>
          <Field label="Guardian Name">
            <input className={INPUT} value={form.guardian_name ?? ""} onChange={(e) => set("guardian_name", e.target.value)} />
          </Field>
          <Field label="Guardian Phone">
            <input className={INPUT} value={form.guardian_phone ?? ""} onChange={(e) => set("guardian_phone", e.target.value)} />
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

export default function StudentsPage() {
  const [data, setData]         = useState<StudentList | null>(null);
  const [classes, setClasses]   = useState<ClassItem[]>([]);
  const [search, setSearch]     = useState("");
  const [classId, setClassId]   = useState<number | null>(null);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(true);
  const [dialog, setDialog]     = useState<Student | null | "new">(null);
  const firstLoad               = useRef(true);

  useEffect(() => { getClasses().then(setClasses).catch(() => {}); }, []);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    getStudents({ search, class_id: classId ?? undefined, page, per_page: PAGE_SIZE })
      .then(setData).catch(() => {}).finally(() => { setLoading(false); firstLoad.current = false; });
  }, [search, classId, page]);

  useEffect(() => { load(); }, [load]);

  const handleDeactivate = async (id: number) => {
    if (!confirm("Deactivate this student?")) return;
    await deactivateStudent(id).catch(() => {});
    load();
  };

  const classOptions = [{ value: null as null, label: "All Classes" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Students</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.total.toLocaleString()} students enrolled` : "Loading…"}
          </p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>Add Student</Button>
      </div>

      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name or admission no…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <Select value={classId} onChange={(v) => { setClassId(v as number | null); setPage(1); }} options={classOptions} className="w-44" />
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Student</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Adm No</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Class</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Guardian</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Status</th>
              <th className="px-4 py-3 w-24" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : data?.items.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-gray-900">{s.first_name} {s.last_name}</p>
                    <p className="text-2xs text-gray-400">{s.gender === "M" ? "Male" : "Female"}</p>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs">{s.admission_no}</td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs">{s.class_name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <p className="text-xs text-gray-700">{s.guardian_name ?? "—"}</p>
                    <p className="text-2xs text-gray-400">{s.guardian_phone ?? ""}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    {s.is_active
                      ? <Badge variant="green" dot>Active</Badge>
                      : <Badge variant="gray" dot>Inactive</Badge>}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => setDialog(s)} className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors">
                        <Edit2 size={13} />
                      </button>
                      {s.is_active && (
                        <button onClick={() => handleDeactivate(s.id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors">
                          <UserX size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
        {!loading && data?.items.length === 0 && (
          <EmptyState icon={Users} title="No students found" description="Try adjusting your search or class filter." />
        )}
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between mt-4 text-xs text-gray-500">
          <span>Page {page} of {data.pages} · {data.total} students</span>
          <div className="flex gap-2">
            <Button variant="outline" size="xs" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <Button variant="outline" size="xs" disabled={page === data.pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}

      {dialog !== null && (
        <StudentDialog
          classes={classes}
          initial={dialog === "new" ? undefined : dialog}
          onSave={() => { setDialog(null); load(); }}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  );
}
