import { useState, useEffect } from "react";
import { GraduationCap, ArrowRight, CheckSquare } from "lucide-react";
import { getClassStatus, getAcademicYears, promoteBatch, type StudentPromotionStatus, type AcademicYear } from "@/api/promotion";
import { getClassList, type ClassRecord } from "@/api/classes";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

export default function PromotionPage() {
  const [classes, setClasses]           = useState<ClassRecord[]>([]);
  const [years, setYears]               = useState<AcademicYear[]>([]);
  const [classId, setClassId]           = useState<number | null>(null);
  const [yearId, setYearId]             = useState<number | null>(null);
  const [toClassId, setToClassId]       = useState<number | null>(null);
  const [students, setStudents]         = useState<StudentPromotionStatus[]>([]);
  const [selected, setSelected]         = useState<number[]>([]);
  const [loading, setLoading]           = useState(false);
  const [promoting, setPromoting]       = useState(false);

  useEffect(() => {
    Promise.all([getClassList(), getAcademicYears()]).then(([cls, yrs]) => {
      setClasses(cls);
      setYears(yrs);
      if (cls.length) setClassId(cls[0].id);
      const cur = yrs.find((y) => y.is_current) || yrs[0];
      if (cur) setYearId(cur.id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!classId || !yearId) return;
    setLoading(true);
    getClassStatus(classId, yearId)
      .then((rows) => { setStudents(rows); setSelected([]); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [classId, yearId]);

  const toggle = (id: number) =>
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);

  const selectAll = () => setSelected(students.filter((s) => !s.promoted).map((s) => s.id));

  const handlePromote = async () => {
    if (!classId || !yearId || !toClassId || !selected.length) return;
    setPromoting(true);
    try {
      await promoteBatch({ class_id: classId, academic_year_id: yearId, to_class_id: toClassId, student_ids: selected });
      const rows = await getClassStatus(classId, yearId);
      setStudents(rows);
      setSelected([]);
    } catch {
      // ignore
    } finally {
      setPromoting(false);
    }
  };

  const classOptions  = classes.map((c) => ({ value: c.id, label: c.name }));
  const yearOptions   = years.map((y) => ({ value: y.id, label: y.label }));
  const notPromoted   = students.filter((s) => !s.promoted);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Promotion</h1>
        <p className="text-sm text-gray-500 mt-0.5">Promote students to the next class</p>
      </div>

      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <Select value={classId} onChange={(v) => setClassId(v as number | null)} options={classOptions} className="w-40" />
        <Select value={yearId}  onChange={(v) => setYearId(v as number | null)}  options={yearOptions}  className="w-40" />
        {selected.length > 0 && (
          <>
            <span className="text-sm text-gray-500">Promote to →</span>
            <Select value={toClassId} onChange={(v) => setToClassId(v as number | null)} options={[{ value: null as null, label: "Select class…" }, ...classOptions]} className="w-40" />
            <Button variant="primary" icon={<ArrowRight size={15} />} onClick={handlePromote} disabled={promoting || !toClassId}>
              {promoting ? "Promoting…" : `Promote ${selected.length}`}
            </Button>
          </>
        )}
        {notPromoted.length > 0 && selected.length === 0 && (
          <Button variant="outline" icon={<CheckSquare size={15} />} onClick={selectAll}>Select all eligible</Button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 w-8"></th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Adm. No</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
              : students.length === 0
              ? (
                <tr>
                  <td colSpan={4} className="py-16">
                    <EmptyState icon={GraduationCap} title="No students" description="Select a class and academic year." />
                  </td>
                </tr>
              )
              : students.map((s) => (
                <tr key={s.id} className={`hover:bg-gray-50 transition-colors ${selected.includes(s.id) ? "bg-violet-50" : ""}`}>
                  <td className="px-4 py-3">
                    {!s.promoted && (
                      <input
                        type="checkbox"
                        checked={selected.includes(s.id)}
                        onChange={() => toggle(s.id)}
                        className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                      />
                    )}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">{s.first_name} {s.last_name}</td>
                  <td className="px-4 py-3 text-gray-500">{s.admission_no}</td>
                  <td className="px-4 py-3">
                    {s.promoted
                      ? <Badge variant="green">Promoted</Badge>
                      : <Badge variant="gray">Pending</Badge>
                    }
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
