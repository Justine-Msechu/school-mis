import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Plus, Edit2, UserX, Download, Heart, User } from "lucide-react";
import { downloadCSV } from "@/utils/export";
import { useAuthStore } from "@/stores/authStore";
import {
  getStudents, createStudent, updateStudent, deactivateStudent,
  getNextAdmissionNo, type Student, type StudentList,
} from "@/api/students";
import { getClasses, type ClassItem } from "@/api/grades";
import { getNgos, type Ngo } from "@/api/ngo";
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
  ngos: Ngo[];
  initial?: Student;
  onSave: () => void;
  onClose: () => void;
}

function StudentDialog({ classes, ngos, initial, onSave, onClose }: StudentDialogProps) {
  const isEdit = !!initial;
  const [form, setForm] = useState({
    first_name:           initial?.first_name           ?? "",
    last_name:            initial?.last_name            ?? "",
    admission_no:         initial?.admission_no         ?? "",
    gender:               initial?.gender               ?? "Male",
    class_id:             initial?.class_id             ?? null as number | null,
    date_of_birth:        initial?.date_of_birth        ?? "",
    parent_name:          initial?.parent_name          ?? "",
    parent_phone:         initial?.parent_phone         ?? "",
    parent_email:         initial?.parent_email         ?? "",
    address:              initial?.address              ?? "",
    notes:                initial?.notes                ?? "",
    student_category:     initial?.student_category     ?? "regular",
    student_type:         initial?.student_type         ?? "Day",
    sponsorship_type:     initial?.sponsorship_type     ?? "none",
    sponsor_ngo_id:       initial?.sponsor_ngo_id       ?? null as number | null,
    sponsor_name:         initial?.sponsor_name         ?? "",
    sponsor_phone:        initial?.sponsor_phone        ?? "",
    sponsor_relationship: initial?.sponsor_relationship ?? "",
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
        admission_no:         form.admission_no.trim() || undefined,
        date_of_birth:        form.date_of_birth        || null,
        parent_name:          form.parent_name          || null,
        parent_phone:         form.parent_phone         || null,
        parent_email:         form.parent_email         || null,
        address:              form.address              || null,
        notes:                form.notes                || null,
        sponsor_ngo_id:       form.sponsorship_type === "ngo"        ? form.sponsor_ngo_id       : null,
        sponsor_name:         form.sponsorship_type === "individual" ? form.sponsor_name         : null,
        sponsor_phone:        form.sponsorship_type === "individual" ? form.sponsor_phone        : null,
        sponsor_relationship: form.sponsorship_type === "individual" ? form.sponsor_relationship : null,
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

  const backgroundOptions = [
    { value: "regular",    label: "Regular" },
    { value: "orphan",     label: "Orphan" },
    { value: "vulnerable", label: "Vulnerable / At-risk" },
    { value: "staff_child",label: "Staff Child" },
  ];
  const typeOptions = [
    { value: "Day",      label: "Day Scholar" },
    { value: "Boarding", label: "Boarding" },
  ];

  return (
    <div className="modal-overlay">
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
          <Field label="Background">
            <select className={INPUT} value={form.student_category}
              onChange={(e) => set("student_category", e.target.value)}>
              {backgroundOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
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

        {/* Sponsorship section */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <Heart size={12} className="text-violet-500" />
            Sponsorship
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field label="Sponsored by">
                <div className="flex gap-2">
                  {[
                    { value: "none",       label: "None" },
                    { value: "ngo",        label: "NGO / Organisation" },
                    { value: "individual", label: "Individual" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => set("sponsorship_type", opt.value)}
                      className={`flex-1 py-2 text-xs font-medium rounded-lg border-2 transition-colors
                        ${form.sponsorship_type === opt.value
                          ? "border-violet-500 bg-violet-50 text-violet-700"
                          : "border-gray-200 text-gray-500 hover:border-gray-300"}`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </Field>
            </div>

            {form.sponsorship_type === "ngo" && (
              <div className="col-span-2">
                <Field label="NGO / Organisation *">
                  <select
                    className={INPUT}
                    value={form.sponsor_ngo_id ?? ""}
                    onChange={(e) => set("sponsor_ngo_id", e.target.value ? Number(e.target.value) : null)}
                  >
                    <option value="">Select NGO…</option>
                    {ngos.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
                  </select>
                  {ngos.length === 0 && (
                    <p className="text-xs text-amber-600 mt-1">No NGOs registered yet. Add one from the NGO Partners page first.</p>
                  )}
                </Field>
              </div>
            )}

            {form.sponsorship_type === "individual" && (
              <>
                <Field label="Sponsor Name *">
                  <input className={INPUT} value={form.sponsor_name ?? ""}
                    onChange={(e) => set("sponsor_name", e.target.value)}
                    placeholder="Full name of sponsor" />
                </Field>
                <Field label="Sponsor Phone">
                  <input className={INPUT} value={form.sponsor_phone ?? ""}
                    onChange={(e) => set("sponsor_phone", e.target.value)} />
                </Field>
                <div className="col-span-2">
                  <Field label="Relationship / How they know the student">
                    <input className={INPUT} value={form.sponsor_relationship ?? ""}
                      onChange={(e) => set("sponsor_relationship", e.target.value)}
                      placeholder="e.g. Uncle, Church, Community leader, Employer" />
                  </Field>
                </div>
              </>
            )}
          </div>
        </div>

        <Field label="Notes">
          <textarea
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none mt-3"
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

const BACKGROUND_LABELS: Record<string, { label: string; color: string }> = {
  orphan:     { label: "Orphan",     color: "bg-purple-50 text-purple-700" },
  vulnerable: { label: "Vulnerable", color: "bg-orange-50 text-orange-700" },
  staff_child:{ label: "Staff Child",color: "bg-blue-50 text-blue-700" },
};

const SPONSORSHIP_LABELS: Record<string, { label: string; color: string }> = {
  ngo:        { label: "NGO Sponsored",        color: "bg-violet-50 text-violet-700" },
  individual: { label: "Individually Sponsored", color: "bg-emerald-50 text-emerald-700" },
};

export default function StudentsPage() {
  const { can } = useAuthStore();
  const [data, setData]         = useState<StudentList | null>(null);
  const [classes, setClasses]   = useState<ClassItem[]>([]);
  const [ngos, setNgos]         = useState<Ngo[]>([]);
  const [search, setSearch]     = useState("");
  const [classId, setClassId]   = useState<number | null>(null);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(true);
  const [dialog, setDialog]     = useState<Student | null | "new">(null);
  const firstLoad               = useRef(true);

  useEffect(() => {
    getClasses().then(setClasses).catch(() => {});
    getNgos().then(setNgos).catch(() => {});
  }, []);

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
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5 md:mb-6">
        <div>
          <h1 className="text-lg md:text-xl font-bold text-gray-900">Students</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.total.toLocaleString()} students enrolled` : "Loading…"}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
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

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[160px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name or admission no…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <Select value={classId} onChange={(v) => { setClassId(v as number | null); setPage(1); }} options={classOptions} className="w-40" />
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="table-scroll">
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
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {s.gender && (
                        <span className="text-2xs text-gray-400">
                          {s.gender === "Male" || s.gender === "M" ? "Male" : "Female"}
                        </span>
                      )}
                      {s.student_category && BACKGROUND_LABELS[s.student_category] && (
                        <span className={`text-2xs font-medium px-1.5 py-0.5 rounded-full ${BACKGROUND_LABELS[s.student_category].color}`}>
                          {BACKGROUND_LABELS[s.student_category].label}
                        </span>
                      )}
                      {s.sponsorship_type && s.sponsorship_type !== "none" && SPONSORSHIP_LABELS[s.sponsorship_type] && (
                        <span className={`text-2xs font-medium px-1.5 py-0.5 rounded-full ${SPONSORSHIP_LABELS[s.sponsorship_type].color}`}>
                          {SPONSORSHIP_LABELS[s.sponsorship_type].label}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs font-mono">{s.admission_no}</td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs">{s.class_name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    {s.sponsorship_type === "ngo" && s.sponsor_ngo_id ? (
                      <>
                        <p className="text-xs text-gray-700">
                          {ngos.find((n) => n.id === s.sponsor_ngo_id)?.name ?? "NGO"}
                        </p>
                        <p className="text-2xs text-gray-400">{s.parent_name ?? ""}</p>
                      </>
                    ) : s.sponsorship_type === "individual" && s.sponsor_name ? (
                      <>
                        <p className="text-xs text-gray-700">{s.sponsor_name}</p>
                        <p className="text-2xs text-gray-400">{s.sponsor_relationship ?? s.sponsor_phone ?? ""}</p>
                      </>
                    ) : (
                      <>
                        <p className="text-xs text-gray-700">{s.parent_name ?? "—"}</p>
                        <p className="text-2xs text-gray-400">{s.parent_phone ?? ""}</p>
                      </>
                    )}
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
        </div>
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
          ngos={ngos}
          initial={dialog === "new" ? undefined : dialog}
          onSave={() => { setDialog(null); load(); }}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  );
}
