import { useEffect, useState } from "react";
import { BookOpen, Calendar, Clock, User } from "lucide-react";
import {
  getStudentProfile, getStudentGrades, getStudentAttendance, getStudentTimetable,
  type StudentProfile, type PortalGrade, type AttendanceResponse, type TimetableResponse,
} from "@/api/portal";

type Tab = "grades" | "attendance" | "timetable";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const fmt = (n: number) => n ?? 0;

function GradesTab({ grades }: { grades: PortalGrade[] }) {
  // Group by exam
  const exams: Record<string, PortalGrade[]> = {};
  for (const g of grades) {
    const key = `${g.year_label ?? ""} — ${g.exam_name} (${g.term})`;
    if (!exams[key]) exams[key] = [];
    exams[key].push(g);
  }

  if (grades.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No approved grades yet.</p>;
  }

  return (
    <div className="space-y-6">
      {Object.entries(exams).map(([exam, rows]) => (
        <div key={exam}>
          <h3 className="text-sm font-semibold text-gray-600 mb-2">{exam}</h3>
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase" style={{ background: "var(--color-surface-2)" }}>
                  <th className="px-4 py-2">Subject</th>
                  <th className="px-4 py-2 text-right">Score</th>
                  <th className="px-4 py-2 text-right">Grade</th>
                  <th className="px-4 py-2 hidden sm:table-cell">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((g, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                    <td className="px-4 py-2.5 font-medium">{g.subject_name}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
                      {fmt(g.score)}/{fmt(g.max_score)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        g.grade_letter === "A" ? "bg-green-100 text-green-700" :
                        g.grade_letter === "B" ? "bg-blue-100 text-blue-700" :
                        g.grade_letter === "C" ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      }`}>{g.grade_letter ?? "—"}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs hidden sm:table-cell">{g.remarks ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function AttendanceTab({ data }: { data: AttendanceResponse }) {
  const { summary, records } = data;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Attendance Rate", value: `${summary.rate}%`, color: summary.rate >= 80 ? "text-green-600" : "text-red-600" },
          { label: "Present",  value: summary.present, color: "text-green-600" },
          { label: "Absent",   value: summary.absent,  color: "text-red-600" },
          { label: "Late",     value: summary.late,    color: "text-yellow-600" },
        ].map(s => (
          <div key={s.label} className="rounded-xl border p-4 text-center" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase" style={{ background: "var(--color-surface-2)" }}>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2 hidden sm:table-cell">Notes</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr key={i} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                <td className="px-4 py-2.5 tabular-nums text-gray-600">{r.date}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    r.status === "present" ? "bg-green-100 text-green-700" :
                    r.status === "absent"  ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{r.status}</span>
                </td>
                <td className="px-4 py-2.5 text-gray-400 text-xs hidden sm:table-cell">{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {records.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">No attendance records in the last 60 days.</p>
        )}
      </div>
    </div>
  );
}

function TimetableTab({ data }: { data: TimetableResponse }) {
  if (data.slots.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No active timetable found.</p>;
  }

  const byDay: Record<number, typeof data.slots> = {};
  for (const s of data.slots) {
    if (!byDay[s.day_of_week]) byDay[s.day_of_week] = [];
    byDay[s.day_of_week].push(s);
  }

  return (
    <div className="space-y-5">
      {Object.entries(byDay).map(([day, slots]) => (
        <div key={day}>
          <h3 className="text-sm font-semibold text-gray-600 mb-2">{DAYS[+day - 1] ?? `Day ${day}`}</h3>
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
            <table className="w-full text-sm">
              <tbody>
                {slots.map((s, i) => (
                  <tr key={i} className={`border-t ${s.is_break ? "opacity-50" : ""}`} style={{ borderColor: "var(--color-border)" }}>
                    <td className="px-4 py-2.5 text-xs text-gray-400 tabular-nums whitespace-nowrap">
                      {s.start_time}–{s.end_time}
                    </td>
                    <td className="px-4 py-2.5 font-medium">
                      {s.is_break ? <span className="text-gray-400">Break</span> : s.subject_name}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs hidden sm:table-cell">{s.teacher_name ?? ""}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs hidden sm:table-cell">{s.room ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function StudentPortalPage() {
  const [tab, setTab]             = useState<Tab>("grades");
  const [profile, setProfile]     = useState<StudentProfile | null>(null);
  const [grades, setGrades]       = useState<PortalGrade[]>([]);
  const [attendance, setAttendance] = useState<AttendanceResponse | null>(null);
  const [timetable, setTimetable] = useState<TimetableResponse | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");

  useEffect(() => {
    Promise.all([getStudentProfile(), getStudentGrades()])
      .then(([p, g]) => { setProfile(p); setGrades(g); })
      .catch(() => setError("Failed to load portal data."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab === "attendance" && !attendance) {
      getStudentAttendance().then(setAttendance).catch(() => {});
    }
    if (tab === "timetable" && !timetable) {
      getStudentTimetable().then(setTimetable).catch(() => {});
    }
  }, [tab]);

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "grades",     label: "Grades",     icon: <BookOpen size={15} /> },
    { key: "attendance", label: "Attendance", icon: <Calendar size={15} /> },
    { key: "timetable",  label: "Timetable",  icon: <Clock size={15} /> },
  ];

  if (loading) return <div className="flex justify-center py-16"><div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (error)   return <p className="text-red-500 text-sm text-center py-8">{error}</p>;

  return (
    <div className="space-y-5">
      {/* Profile card */}
      {profile && (
        <div className="rounded-2xl border p-4 flex items-center gap-4" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <div className="w-12 h-12 rounded-full bg-violet-100 flex items-center justify-center flex-shrink-0">
            <User size={22} className="text-violet-600" />
          </div>
          <div>
            <div className="font-semibold" style={{ color: "var(--color-on-surface)" }}>
              {profile.first_name} {profile.last_name}
            </div>
            <div className="text-sm text-gray-500">
              {profile.admission_no} · {profile.class_name ?? "No class"} · {profile.year_label ?? ""}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b" style={{ borderColor: "var(--color-border)" }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.key
                ? "border-violet-600 text-violet-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {tab === "grades"     && <GradesTab grades={grades} />}
        {tab === "attendance" && (attendance ? <AttendanceTab data={attendance} /> : <div className="flex justify-center py-8"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>)}
        {tab === "timetable"  && (timetable  ? <TimetableTab data={timetable}   /> : <div className="flex justify-center py-8"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>)}
      </div>
    </div>
  );
}
