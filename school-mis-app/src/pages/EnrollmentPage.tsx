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

interface AcademicYear { id: number; name: string; is_current: number; }
interface ClassRow { id: number; name: string; }

export default function EnrollmentPage() {
  const toast = useToast();
  const firstLoad = useRef(true);
  const [loading, setLoading] = useState(true);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [year, setYear] = useState<number | "">("");
  const [selectedClass, setSelectedClass] = useState<number | "">("");
  const [headcount, setHeadcount] = useState<HeadcountRow[]>([]);
  const [roll, setRoll] = useState<Enrollment[]>([]);
  const [search, setSearch] = useState("");
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollForm, setEnrollForm] = useState({ student_id: "", class_id: "", academic_year_id: "" });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/settings/academic-years").then((r) => r.data),
      api.get("/classes").then((r) => r.data),
    ]).then(([yrs, cls]) => {
      setYears(yrs);
      setClasses(cls.items || cls);
      const current = yrs.find((y: AcademicYear) => y.is_current);
      if (current) setYear(current.id);
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

  const headcountColumns: Column<HeadcountRow>[] = [
    { key: "class_name", header: "Class", sortable: true },
    { key: "enrolled", header: "Enrolled", sortable: true, render: (row) => <span className="font-semibold text-green-700">{row.enrolled}</span> },
    { key: "transferred", header: "Transferred", sortable: true, render: (row) => <span>{row.transferred}</span> },
    { key: "withdrawn", header: "Withdrawn", sortable: true, render: (row) => <span>{row.withdrawn}</span> },
  ];

  const rollColumns: Column<Enrollment>[] = [
    { key: "admission_no", header: "Adm No", sortable: true },
    { key: "student_name", header: "Student", sortable: true },
    { key: "status", header: "Status", sortable: true, render: (row) => (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        row.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
      }`}>{row.status}</span>
    )},
    { key: "enrollment_date", header: "Enrolled", sortable: true },
  ];

  const handleEnroll = async () => {
    if (!enrollForm.student_id || !enrollForm.class_id || !enrollForm.academic_year_id) return;
    setSubmitting(true);
    try {
      await enrollStudent({
        student_id: Number(enrollForm.student_id),
        class_id: Number(enrollForm.class_id),
        academic_year_id: Number(enrollForm.academic_year_id),
      });
      toast.success("Student enrolled successfully");
      setEnrollOpen(false);
      setEnrollForm({ student_id: "", class_id: "", academic_year_id: "" });
      if (year) getHeadcount(year as number).then(setHeadcount);
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
          onChange={(e) => setYear(Number(e.target.value))}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
        >
          <option value="">Select year</option>
          {years.map((y) => <option key={y.id} value={y.id}>{y.name}</option>)}
        </select>
        <SearchInput value={search} onChange={setSearch} placeholder="Search classes…" className="w-56" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50 flex items-center gap-2">
              <Users size={16} className="text-violet-600" />
              <h2 className="text-sm font-semibold text-gray-800">Class Headcount</h2>
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
                {selectedClass ? classes.find((c) => c.id === selectedClass)?.name || "Class Roll" : "Select a class"}
              </h2>
            </div>
            {roll.length > 0 ? (
              <DataTable<Enrollment>
                columns={rollColumns}
                rows={roll}
                loading={false}
              />
            ) : (
              <div className="p-8 text-center text-sm text-gray-400">
                {selectedClass ? "No enrollments found" : "Click a class to view roll"}
              </div>
            )}
          </div>
        </div>
      </div>

      <Modal open={enrollOpen} onClose={() => setEnrollOpen(false)} title="Enroll Student"
        footer={
          <>
            <button onClick={() => setEnrollOpen(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
            <button onClick={handleEnroll} disabled={submitting} className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {submitting ? "Enrolling…" : "Enroll"}
            </button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <FormField label="Student ID" required>
            <input
              type="number"
              value={enrollForm.student_id}
              onChange={(e) => setEnrollForm((f) => ({ ...f, student_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="Enter student ID"
            />
          </FormField>
          <FormField label="Class" required>
            <select
              value={enrollForm.class_id}
              onChange={(e) => setEnrollForm((f) => ({ ...f, class_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
            >
              <option value="">Select class</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </FormField>
          <FormField label="Academic Year" required>
            <select
              value={enrollForm.academic_year_id}
              onChange={(e) => setEnrollForm((f) => ({ ...f, academic_year_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
            >
              <option value="">Select year</option>
              {years.map((y) => <option key={y.id} value={y.id}>{y.name}</option>)}
            </select>
          </FormField>
        </div>
      </Modal>
    </div>
  );
}
