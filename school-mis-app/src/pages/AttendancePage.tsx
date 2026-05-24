import { useState, useEffect } from "react";
import { CalendarCheck, Save } from "lucide-react";
import { getAttendanceSheet, saveAttendance, type AttendanceRow } from "@/api/attendance";
import { getClassList, type ClassRecord } from "@/api/classes";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";

const STATUS_OPTIONS = ["present", "absent", "late", "excused"];
const STATUS_COLOR: Record<string, string> = {
  present: "bg-emerald-100 text-emerald-700",
  absent:  "bg-red-100 text-red-700",
  late:    "bg-amber-100 text-amber-700",
  excused: "bg-blue-100 text-blue-700",
};

export default function AttendancePage() {
  const [classes, setClasses]   = useState<ClassRecord[]>([]);
  const [classId, setClassId]   = useState<number | null>(null);
  const [date, setDate]         = useState(new Date().toISOString().slice(0, 10));
  const [rows, setRows]         = useState<AttendanceRow[]>([]);
  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);

  useEffect(() => {
    getClassList().then((cls) => { setClasses(cls); if (cls.length) setClassId(cls[0].id); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!classId) return;
    setLoading(true);
    getAttendanceSheet(classId, date)
      .then((sheet) => setRows(sheet.rows))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [classId, date]);

  const setStatus = (id: number, status: string) =>
    setRows((prev) => prev.map((r) => r.id === id ? { ...r, status } : r));

  const handleSave = async () => {
    if (!classId) return;
    setSaving(true);
    try {
      await saveAttendance(classId, date, rows.map((r) => ({ student_id: r.id, status: r.status, remarks: r.remarks })));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const classOptions = [{ value: null as null, label: "Select class…" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Attendance</h1>
          <p className="text-sm text-gray-500 mt-0.5">Mark daily attendance by class</p>
        </div>
        <Button variant="primary" icon={<Save size={15} />} onClick={handleSave} disabled={saving || !rows.length}>
          {saved ? "Saved!" : saving ? "Saving…" : "Save"}
        </Button>
      </div>

      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <Select
          value={classId}
          onChange={(v) => setClassId(v as number | null)}
          options={classOptions}
          className="w-48"
        />
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
        <span className="text-sm text-gray-500">
          {rows.length > 0 && `${rows.filter((r) => r.status === "present").length} / ${rows.length} present`}
        </span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 w-8">#</th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Adm. No</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={4} className="py-12 text-center text-gray-400 text-sm">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-16">
                  <EmptyState icon={CalendarCheck} title="No students" description="Select a class to mark attendance." />
                </td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-2.5 font-medium text-gray-900">{r.first_name} {r.last_name}</td>
                  <td className="px-4 py-2.5 text-gray-500">{r.admission_no}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1.5 flex-wrap">
                      {STATUS_OPTIONS.map((s) => (
                        <button
                          key={s}
                          onClick={() => setStatus(r.id, s)}
                          className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors capitalize
                            ${r.status === s ? STATUS_COLOR[s] : "bg-gray-100 text-gray-500 hover:bg-gray-200"}`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
