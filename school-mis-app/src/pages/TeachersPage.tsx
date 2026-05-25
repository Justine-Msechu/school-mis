import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Plus, Edit2, Mail, Phone, Users, Download } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { getTeachers, createTeacher, updateTeacher, getNextEmployeeNo, type Teacher } from "@/api/teachers";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

interface TeacherDialogProps {
  initial?: Teacher;
  onSave: () => void;
  onClose: () => void;
}

function TeacherDialog({ initial, onSave, onClose }: TeacherDialogProps) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    first_name:             initial?.first_name             ?? "",
    last_name:              initial?.last_name              ?? "",
    employee_no:            initial?.employee_no            ?? "",
    gender:                 initial?.gender                 ?? "M",
    phone:                  initial?.phone                  ?? "",
    email:                  initial?.email                  ?? "",
    subject_specialization: initial?.subject_specialization ?? "",
    qualification:          initial?.qualification          ?? "",
    joining_date:           initial?.joining_date           ?? "",
  });
  const [empPreview, setEmpPreview]       = useState("");
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  useEffect(() => {
    if (!isEdit) {
      setLoadingPreview(true);
      getNextEmployeeNo()
        .then((no) => setEmpPreview(no))
        .catch(() => setEmpPreview(""))
        .finally(() => setLoadingPreview(false));
    }
  }, [isEdit]);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

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
        employee_no:            form.employee_no.trim()            || undefined,
        phone:                  form.phone                         || null,
        email:                  form.email                         || null,
        subject_specialization: form.subject_specialization        || null,
        qualification:          form.qualification                 || null,
        joining_date:           form.joining_date                  || null,
      };
      if (isEdit) {
        await updateTeacher(initial!.id, payload);
      } else {
        await createTeacher(payload);
      }
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save teacher.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{isEdit ? "Edit Teacher" : "Add Teacher"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <Field label="First Name *">
            <input className={INPUT} value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
          </Field>
          <Field label="Last Name *">
            <input className={INPUT} value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
          </Field>
          <Field label={isEdit ? "Employee No" : "Employee No (leave blank to auto-generate)"}>
            <div className="relative">
              <input
                className={INPUT + " font-mono"}
                value={form.employee_no}
                onChange={(e) => set("employee_no", e.target.value)}
                placeholder={isEdit ? "" : loadingPreview ? "Loading…" : empPreview}
              />
            </div>
            {!isEdit && (
              <p className="text-2xs text-gray-400 mt-0.5">Leave blank to auto-assign ({empPreview || "EMP/YYYY/NNNN"})</p>
            )}
          </Field>
          <Field label="Gender">
            <select className={INPUT} value={form.gender} onChange={(e) => set("gender", e.target.value)}>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </Field>
          <Field label="Phone">
            <input className={INPUT} value={form.phone ?? ""} onChange={(e) => set("phone", e.target.value)} />
          </Field>
          <Field label="Email">
            <input type="email" className={INPUT} value={form.email ?? ""} onChange={(e) => set("email", e.target.value)} />
          </Field>
          <Field label="Subject Specialization">
            <input className={INPUT} value={form.subject_specialization ?? ""} onChange={(e) => set("subject_specialization", e.target.value)} />
          </Field>
          <Field label="Qualification">
            <input className={INPUT} value={form.qualification ?? ""} onChange={(e) => set("qualification", e.target.value)} />
          </Field>
          <Field label="Joining Date">
            <input type="date" className={INPUT} value={form.joining_date ?? ""} onChange={(e) => set("joining_date", e.target.value)} />
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

export default function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [search, setSearch]     = useState("");
  const [loading, setLoading]   = useState(true);
  const [dialog, setDialog]     = useState<Teacher | null | "new">(null);
  const firstLoad               = useRef(true);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    getTeachers(search).then(setTeachers).catch(() => {}).finally(() => { setLoading(false); firstLoad.current = false; });
  }, [search]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Teachers</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? "Loading…" : `${teachers.length} staff members`}
          </p>
        </div>
        <div className="flex gap-2">
          {teachers.length > 0 && (
            <button
              onClick={() => downloadCSV("Teachers", ["Emp No","First Name","Last Name","Gender","Specialization","Qualification","Phone","Email","Joined"],
                teachers.map((t) => [t.employee_no, t.first_name, t.last_name, t.gender, t.subject_specialization ?? "", t.qualification ?? "", t.phone ?? "", t.email ?? "", t.joining_date ?? ""]))}
              className="flex items-center gap-1.5 h-9 px-3 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download size={14} /> Export
            </button>
          )}
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>Add Teacher</Button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, employee no…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Employee No</th>
              <th className="px-4 py-3">Specialization</th>
              <th className="px-4 py-3">Contact</th>
              <th className="px-4 py-3">Qualification</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3 w-16" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
              : teachers.length === 0
              ? (
                <tr>
                  <td colSpan={7} className="py-16">
                    <EmptyState icon={Users} title="No teachers found" description="Try adjusting the search query." />
                  </td>
                </tr>
              )
              : teachers.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{t.first_name} {t.last_name}</div>
                    {t.gender && <div className="text-xs text-gray-400">{t.gender === "M" ? "Male" : "Female"}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{t.employee_no || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.subject_specialization || "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      {t.phone && (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <Phone size={11} /> {t.phone}
                        </span>
                      )}
                      {t.email && (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <Mail size={11} /> {t.email}
                        </span>
                      )}
                      {!t.phone && !t.email && "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.qualification || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.joining_date || "—"}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setDialog(t)}
                      className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors"
                    >
                      <Edit2 size={13} />
                    </button>
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>

      {dialog !== null && (
        <TeacherDialog
          initial={dialog === "new" ? undefined : dialog}
          onSave={() => { setDialog(null); load(); }}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  );
}
