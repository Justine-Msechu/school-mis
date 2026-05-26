import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Plus, Edit2, UserX, Download } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { useAuthStore } from "@/stores/authStore";
import {
  getStudents, createStudent, updateStudent, deactivateStudent,
  getNextAdmissionNo, type Student, type StudentList,
} from "@/api/students";
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
const INPUT_MONO = INPUT + " font-mono";

interface StudentDialogProps {
  classes: ClassItem[];
  initial?: Student;
  onSave: () => void;
  onClose: () => void;
}

function StudentDialog({ classes, initial, onSave, onClose }: StudentDialogProps) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    first_name:    initial?.first_name    ?? "",
    last_name:     initial?.last_name     ?? "",
    admission_no:  initial?.admission_no  ?? "",
    gender:        initial?.gender        ?? "Male",
    class_id:      initial?.class_id      ?? null as number | null,
    date_of_birth: initial?.date_of_birth ?? "",
    parent_name:   initial?.parent_name   ?? "",
    parent_phone:  initial?.parent_phone  ?? "",
    parent_email:  initial?.parent_email  ?? "",
    address:       initial?.address       ?? "",
    notes:         initial?.notes         ?? "",
    student_category: initial?.student_category ?? "regular",
    student_type:     (initial as any)?.student_type ?? "Day",
  });
  const [admPreview, setAdmPreview] = useState("");
  const [loadingPreview, setLoadingPreview]  = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  useEffect(() => {
    if (!isEdit) {
      setLoadingPreview(true);
      getNextAdmissionNo()
        .then((no) => setAdmPreview(no))
        .catch(() => setAdmPreview(""))
        .finally(() => setLoadingPreview(false));
    }
  }, [isEdit]);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.first_name || !form.last_name) {
      setError("First name and last name are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...form,
        admission_no:  form.admission_no.trim() || undefined,
        date_of_birth: form.date_of_birth || null,
        parent_name:   form.parent_name   || null,
        parent_phone:  form.parent_phone  || null,
        parent_email:  form.parent_email  || null,
        address:       form.address       || null,
        notes:         form.notes         || null,
      };
      if (isEdit) {
        await updateStudent(initial!.id, payload);
      } else {
        await createStudent(payload);
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

  const categoryOptions = [
    { value: "regular",    label: "Regular" },
    { value: "orphan",     label: "Orphan" },
    { value: "sponsored",  label: "Sponsored" },
    { value: "staff_child",label: "Staff Child" },
  ];
  const typeOptions = [
    { value: "Day",      label: "Day Scholar" },
    { value: "Boarding", label: "Boarding" },
  ];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{isEdit ? "Edit Student" : "Add Student"}</h2>

        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

        <div className="grid grid-cols-2 gap-3">
          <Field label="First Name *">
            <input className={INPUT} value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
          </Field>
          <Field label="Last Name *">
            <input className={INPUT} value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
          </Field>

          <Field label={isEdit ? "Admission No" : "Admission No (leave blank to auto-generate)"}>
            <div className="relative">
              <input
                className={INPUT_MONO}
                value={form.admission_no}
                onChange={(e) => set("admission_no", e.target.value)}
                placeholder={isEdit ? "" : loadingPreview ? "Loading…" : admPreview}
              />
              {!isEdit && !loadingPreview && admPreview && !form.admission_no && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-2xs text-gray-400 pointer-events-none">
                  auto: {admPreview}
                </span>
              )}
            </div>
            {!isEdit && (
              <p className="text-2xs text-gray-400 mt-0.5">Leave blank to auto-assign ({admPreview || "ADM/YYYY/NNNN"})</p>
            )}
          </Field>

          <Field label="Gender">
            <select className={INPUT} value={form.gender} onChange={(e) => set("gender", e.target.value)}>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
          </Field>

          <Field label="Class">
            <Select value={form.class_id} onChange={(v) => set("class_id", v as number | null)} options={classOptions} />
          </Field>
          <Field label="Date of Birth">
            <input type="date" className={INPUT} value={form.date_of_birth ?? ""} onChange={(e) => set("date_of_birth", e.target.value)} />
          </Field>
          <Field label="Type">
            <select className={INPUT} value={form.student_type} onChange={(e) => set("student_type", e.target.value)}>
              {typeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Category">
            <select className={INPUT} value={form.student_category} onChange={(e) => set("student_category", e.target.value)}>
              {categoryOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Parent / Guardian Name">
            <input className={INPUT} value={form.parent_name ?? ""} onChange={(e) => set("parent_name", e.target.value)} />
          </Field>
          <Field label="Parent Phone">
            <input className={INPUT} value={form.parent_phone ?? ""} onChange={(e) => set("parent_phone", e.target.value)} />
          </Field>
          <Field label="Parent Email">
            <input type="email" className={INPUT} value={form.parent_email ?? ""} onChange={(e) => set("parent_email", e.target.value)} />
          </Field>
          <Field label="Address">
            <input className={INPUT} value={form.address ?? ""} onChange={(e) => set("address", e.target.value)} />
          </Field>
        </div>

        <Field label="Notes">
          <textarea
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
            rows={2}
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value)}
          />
        </Field>

        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function StudentsPage() {
  const { can } = useAuthStore();
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
        <div className="flex gap-2">
          {data && data.items.length > 0 && (
            <button
              onClick={() => downloadCSV("Students", ["Adm No","First Name","Last Name","Gender","Class","Parent","Phone","Status"],
                data.items.map((s) => [s.admission_no, s.first_name, s.last_name, s.gender, s.class_name ?? "", s.parent_name ?? "", s.parent_phone ?? "", s.is_active ? "Active" : "Inactive"]))}
              className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download size={14} /> Export
            </button>
          )}
          {can("student.create") && (
            <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>Add Student</Button>
          )}
        </div>
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Parent / Guardian</th>
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
                    <p className="text-2xs text-gray-400">{s.gender === "Male" || s.gender === "M" ? "Male" : "Female"}</p>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs font-mono">{s.admission_no}</td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs">{s.class_name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <p className="text-xs text-gray-700">{s.parent_name ?? "—"}</p>
                    <p className="text-2xs text-gray-400">{s.parent_phone ?? ""}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    {s.is_active
                      ? <Badge variant="green" dot>Active</Badge>
                      : <Badge variant="gray" dot>Inactive</Badge>}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center justify-end gap-1">
                      {can("student.edit") && (
                        <button onClick={() => setDialog(s)} className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors">
                          <Edit2 size={13} />
                        </button>
                      )}
                      {s.is_active && can("student.deactivate") && (
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
