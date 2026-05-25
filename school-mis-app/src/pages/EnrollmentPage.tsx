import { useEffect, useRef, useState } from "react";
import { UserPlus, Users } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import SearchInput from "@/components/ui/SearchInput";
import Modal from "@/components/ui/Modal";
import FormField from "@/components/ui/FormField";
import { DataTable, type Column } from "@/components/data/DataTable";
import { useToast } from "@/components/ui/Toast";
import { getHeadcount, enrollStudent, getClassRoll, type Enrollment, type HeadcountRow } from "@/api/enrollments";
import api from "@/api/client";

interface AcademicYear { id: number; label: string; is_current: number; }
interface ClassRow { id: number; name: string; }
interface StudentOption { id: number; first_name: string; last_name: string; admission_no: string; }

export default function EnrollmentPage() {
  const toast = useToast();
  const firstLoad = useRef(true);
  const [loading, setLoading] = useState(true);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [year, setYear] = useState<number | "">("");
  const [selectedClass, setSelectedClass] = useState<number | "">("");
  const [headcount, setHeadcount] = useState<HeadcountRow[]>([]);
  const [roll, setRoll] = useState<Enrollment[]>([]);
  const [search, setSearch] = useState("");
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollForm, setEnrollForm] = useState({ student_id: "", class_id: "", academic_year_id: "" });
  const [studentSearch, setStudentSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/settings/academic-years").then((r) => r.data),
      api.get("/classes").then((r) => r.data),
      api.get("/students").then((r) => r.data),
    ]).then(([yrs, cls, stu]) => {
      setYears(yrs);
      setClasses(cls.items || cls);
      setStudents(stu.items || stu);
      const current = yrs.find((y: AcademicYear) => y.is_current);
      if (current) {
        setYear(current.id);
        setEnrollForm((f) => ({ ...f, academic_year_id: String(current.id) }));
      }
    });
  }, []);

  useEffect(() => {
    if (!year) return;
    if (firstLoad.current) { firstLoad.current = false; setLoading(true); }
    getHeadcount(year as number).then(setHeadcount).finally(() => setLoading(false));
  }, [year]);

  useEffect(() => {
    if (!selectedClass || !year) { setRoll([]); return; }
    getClassRoll(selectedClass as number, year as number).then(setRoll);
  }, [selectedClass, year]);

  const filtered = headcount.filter((r) =>
    r.class_name.toLowerCase().includes(search.toLowerCase())
  );

  const filteredStudents = students.filter((s) => {
    const q = studentSearch.toLowerCase();
    return (
      s.admission_no.toLowerCase().includes(q) ||
      `${s.first_name} ${s.last_name}`.toLowerCase().includes(q)
    );
  });

  const headcountColumns: Column<HeadcountRow>[] = [
    { key: "class_name", header: "Class", sortable: true },
    {
      key: "enrolled", header: "Enrolled", sortable: true,
      render: (row) => <span className="font-semibold text-green-700">{row.enrolled}</span>,
    },
    { key: "transferred", header: "Transferred", sortable: true },
    { key: "withdrawn", header: "Withdrawn", sortable: true },
  ];

  const rollColumns: Column<Enrollment>[] = [
    { key: "admission_no", header: "Adm No", sortable: true },
    { key: "student_name", header: "Student", sortable: true },
    {
      key: "status", header: "Status", sortable: true,
      render: (row) => (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
          row.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
        }`}>{row.status}</span>
      ),
    },
    { key: "enrollment_date", header: "Enrolled On", sortable: true },
  ];

  const handleEnroll = async () => {
    if (!enrollForm.student_id || !enrollForm.class_id || !enrollForm.academic_year_id) {
      toast.error("Please fill all fields");
      return;
    }
    setSubmitting(true);
    try {
      await enrollStudent({
        student_id: Number(enrollForm.student_id),
        class_id: Number(enrollForm.class_id),
        academic_year_id: Number(enrollForm.academic_year_id),
      });
      toast.success("Student enrolled successfully");
      setEnrollOpen(false);
      setEnrollForm((f) => ({ ...f, student_id: "", class_id: "" }));
      setStudentSearch("");
      if (year) getHeadcount(year as number).then(setHeadcount);
      if (selectedClass && year) getClassRoll(selectedClass as number, year as number).then(setRoll);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to enroll student");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6">
      <PageHeader
        title="Enrollment"
        subtitle="Manage student class enrollment and transfers"
        actions={
          <button
            onClick={() => setEnrollOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition-colors"
          >
            <UserPlus size={15} />
            Enroll Student
          </button>
        }
      />

      <div className="flex gap-3 mb-6">
        <select
          value={year}
          onChange={(e) => { setYear(Number(e.target.value)); setSelectedClass(""); }}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
        >
          <option value="">Select year</option>
          {years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
        </select>
        <SearchInput value={search} onChange={setSearch} placeholder="Search classes…" className="w-56" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50 flex items-center gap-2">
              <Users size={16} className="text-violet-600" />
              <h2 className="text-sm font-semibold text-gray-800">Class Headcount</h2>
              <span className="ml-auto text-xs text-gray-400">Click a class to view its roll</span>
            </div>
            <DataTable<HeadcountRow>
              columns={headcountColumns}
              rows={filtered}
              loading={loading}
              onRowClick={(row) => setSelectedClass(row.class_id)}
            />
          </div>
        </div>

        <div>
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50">
              <h2 className="text-sm font-semibold text-gray-800">
                {selectedClass ? classes.find((c) => c.id === selectedClass)?.name || "Class Roll" : "Class Roll"}
              </h2>
            </div>
            {selectedClass ? (
              roll.length > 0 ? (
                <DataTable<Enrollment>
                  columns={rollColumns}
                  rows={roll}
                  loading={false}
                />
              ) : (
                <div className="p-8 text-center text-sm text-gray-400">No enrollments found</div>
              )
            ) : (
              <div className="p-8 text-center text-sm text-gray-400">Click a class to view its roll</div>
            )}
          </div>
        </div>
      </div>

      <Modal
        open={enrollOpen}
        onClose={() => { setEnrollOpen(false); setStudentSearch(""); }}
        title="Enroll Student"
        footer={
          <>
            <button
              onClick={() => { setEnrollOpen(false); setStudentSearch(""); }}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleEnroll}
              disabled={submitting}
              className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50"
            >
              {submitting ? "Enrolling…" : "Enroll"}
            </button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <FormField label="Student" required>
            <input
              type="text"
              value={studentSearch}
              onChange={(e) => { setStudentSearch(e.target.value); setEnrollForm((f) => ({ ...f, student_id: "" })); }}
              placeholder="Search by name or admission no…"
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30 w-full"
            />
            {studentSearch && !enrollForm.student_id && (
              <div className="mt-1 border border-gray-200 rounded-lg bg-white shadow-sm max-h-40 overflow-y-auto">
                {filteredStudents.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-400">No students found</div>
                ) : (
                  filteredStudents.slice(0, 8).map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => {
                        setEnrollForm((f) => ({ ...f, student_id: String(s.id) }));
                        setStudentSearch(`${s.first_name} ${s.last_name} (${s.admission_no})`);
                      }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-violet-50 border-b last:border-0"
                    >
                      <span className="font-medium">{s.first_name} {s.last_name}</span>
                      <span className="ml-2 text-gray-400 text-xs">{s.admission_no}</span>
                    </button>
                  ))
                )}
              </div>
            )}
            {enrollForm.student_id && (
              <p className="text-xs text-green-600 mt-1">Student ID {enrollForm.student_id} selected</p>
            )}
          </FormField>

          <FormField label="Class" required>
            <select
              value={enrollForm.class_id}
              onChange={(e) => setEnrollForm((f) => ({ ...f, class_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30 w-full"
            >
              <option value="">Select class</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </FormField>

          <FormField label="Academic Year" required>
            <select
              value={enrollForm.academic_year_id}
              onChange={(e) => setEnrollForm((f) => ({ ...f, academic_year_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30 w-full"
            >
              <option value="">Select year</option>
              {years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </FormField>
        </div>
      </Modal>
    </div>
  );
}
