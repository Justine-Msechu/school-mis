import { useEffect, useState } from "react";
import { X, Plus, Trash2, AlertTriangle, BookOpen, Home } from "lucide-react";
import {
  listTeacherAssignments, assignTeacher, removeTeacherAssignment,
  listClassTeacherAssignments, assignClassTeacher, removeClassTeacherAssignment,
  type TeacherAssignment, type ClassTeacherAssignment,
} from "@/api/rbac";
import { getClasses } from "@/api/grades";
import type { Teacher } from "@/api/teachers";
import { useToast } from "@/components/ui/Toast";

// Fetch all subjects (no class filter)
async function getAllSubjects(): Promise<{ id: number; name: string }[]> {
  const { default: api } = await import("@/api/client");
  const { data } = await api.get("/grades/subjects");
  return data;
}

async function getCurrentYear(): Promise<{ id: number; label: string } | null> {
  const { default: api } = await import("@/api/client");
  const { data } = await api.get<{ id: number; label: string; is_current: number }[]>("/settings/academic-years");
  return data.find((y) => y.is_current) ?? data[0] ?? null;
}

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/40 bg-white";
const BTN_SM = "flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-lg transition-colors";

interface Props {
  teacher: Teacher;
  onClose: () => void;
}

export default function TeacherAssignmentsPanel({ teacher, onClose }: Props) {
  const toast = useToast();
  const fullName = `${teacher.first_name} ${teacher.last_name}`;

  const [subjects, setSubjects]         = useState<{ id: number; name: string }[]>([]);
  const [classes, setClasses]           = useState<{ id: number; name: string }[]>([]);
  const [yearId, setYearId]             = useState<number | null>(null);
  const [assignments, setAssignments]   = useState<TeacherAssignment[]>([]);
  const [classAssigns, setClassAssigns] = useState<ClassTeacherAssignment[]>([]);
  const [loading, setLoading]           = useState(true);

  // Add subject assignment form
  const [addSubjectId, setAddSubjectId] = useState<number | "">("");
  const [addClassId, setAddClassId]     = useState<number | "">("");
  const [adding, setAdding]             = useState(false);

  // Add class teacher form
  const [addCTClassId, setAddCTClassId] = useState<number | "">("");
  const [addingCT, setAddingCT]         = useState(false);

  const userId = teacher.user_id;

  const load = async () => {
    setLoading(true);
    try {
      const [subs, cls, yr, asgn, ctAsgn] = await Promise.all([
        getAllSubjects(),
        getClasses(),
        getCurrentYear(),
        userId ? listTeacherAssignments({ user_id: userId }) : Promise.resolve([]),
        listClassTeacherAssignments(),
      ]);
      setSubjects(subs);
      setClasses(cls);
      if (yr) setYearId(yr.id);
      setAssignments(asgn.filter((a) => a.user_id === userId));
      setClassAssigns(ctAsgn.filter((a) => a.user_id === userId));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAddSubject = async () => {
    if (!addSubjectId || !addClassId || !userId) return;
    setAdding(true);
    try {
      await assignTeacher({ user_id: userId, subject_id: +addSubjectId, class_id: +addClassId, academic_year_id: yearId });
      toast.success("Assignment added");
      setAddSubjectId("");
      setAddClassId("");
      await load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Failed to assign");
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveSubject = async (id: number) => {
    try {
      await removeTeacherAssignment(id);
      toast.success("Assignment removed");
      await load();
    } catch {
      toast.error("Failed to remove");
    }
  };

  const handleAddClassTeacher = async () => {
    if (!addCTClassId || !userId) return;
    setAddingCT(true);
    try {
      await assignClassTeacher({ user_id: userId, class_id: +addCTClassId, academic_year_id: yearId });
      toast.success("Class teacher assigned");
      setAddCTClassId("");
      await load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Failed to assign");
    } finally {
      setAddingCT(false);
    }
  };

  const handleRemoveClassTeacher = async (id: number) => {
    try {
      await removeClassTeacherAssignment(id);
      toast.success("Class teacher assignment removed");
      await load();
    } catch {
      toast.error("Failed to remove");
    }
  };

  // Classes already assigned as class teacher (to exclude from dropdown)
  const ctClassIds = new Set(classAssigns.map((a) => a.class_id));
  // Already assigned subject+class combos (to show duplicate warning)
  const assignedKeys = new Set(assignments.map((a) => `${a.subject_id}-${a.class_id}`));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white w-full sm:rounded-2xl sm:max-w-2xl shadow-2xl flex flex-col max-h-[92vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <p className="text-base font-bold text-gray-900">{fullName}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {teacher.subject_specialization
                ? `Specialisation: ${teacher.subject_specialization}`
                : "No specialisation recorded"}
              {teacher.username && (
                <span className="ml-2 px-1.5 py-0.5 bg-violet-100 text-violet-700 rounded text-xs">
                  @{teacher.username}
                </span>
              )}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* No user account warning */}
        {!userId && (
          <div className="mx-6 mt-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2">
            <AlertTriangle size={15} className="text-amber-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-800">
              This teacher has no linked user account. Go to <strong>Settings → Users</strong> to create an account and link it to this teacher record. Assignments require a user account.
            </p>
          </div>
        )}

        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-6">

          {/* ── Subject Assignments ─────────────────────────────────────────── */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <BookOpen size={15} className="text-violet-600" />
              <h3 className="text-sm font-semibold text-gray-800">Subject Assignments</h3>
              {assignments.length > 0 && (
                <span className="px-1.5 py-0.5 bg-violet-100 text-violet-700 rounded-full text-xs font-medium">
                  {assignments.length}
                </span>
              )}
            </div>

            {loading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />)}
              </div>
            ) : assignments.length === 0 ? (
              <p className="text-xs text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded-xl">
                No subject assignments yet
              </p>
            ) : (
              <div className="rounded-xl border border-gray-200 overflow-hidden">
                <div className="table-scroll"><table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide text-left">
                      <th className="px-4 py-2.5">Subject</th>
                      <th className="px-4 py-2.5">Class</th>
                      <th className="px-4 py-2.5">Year</th>
                      <th className="px-4 py-2.5 w-10" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {assignments.map((a) => (
                      <tr key={a.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2.5 font-medium text-gray-800">{a.subject_name}</td>
                        <td className="px-4 py-2.5 text-gray-600">{a.class_name}</td>
                        <td className="px-4 py-2.5 text-gray-500 text-xs">{a.year_label ?? "—"}</td>
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => handleRemoveSubject(a.id)}
                            className="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            )}

            {/* Add subject assignment form */}
            {userId && (
              <div className="mt-3 flex gap-2 items-end">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Subject</label>
                  <select
                    className={INPUT}
                    value={addSubjectId}
                    onChange={(e) => setAddSubjectId(e.target.value ? +e.target.value : "")}
                  >
                    <option value="">Select subject…</option>
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Class</label>
                  <select
                    className={INPUT}
                    value={addClassId}
                    onChange={(e) => setAddClassId(e.target.value ? +e.target.value : "")}
                  >
                    <option value="">Select class…</option>
                    {classes.map((c) => {
                      const isDup = addSubjectId && assignedKeys.has(`${addSubjectId}-${c.id}`);
                      return (
                        <option key={c.id} value={c.id} disabled={!!isDup}>
                          {c.name}{isDup ? " (already assigned)" : ""}
                        </option>
                      );
                    })}
                  </select>
                </div>
                <button
                  onClick={handleAddSubject}
                  disabled={!addSubjectId || !addClassId || adding}
                  className={`${BTN_SM} bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  <Plus size={13} /> {adding ? "Adding…" : "Add"}
                </button>
              </div>
            )}
          </section>

          {/* ── Class Teacher Assignment ────────────────────────────────────── */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Home size={15} className="text-emerald-600" />
              <h3 className="text-sm font-semibold text-gray-800">Class Teacher (Homeroom)</h3>
            </div>

            {!loading && classAssigns.length === 0 && (
              <p className="text-xs text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded-xl">
                Not assigned as class teacher for any class
              </p>
            )}

            {classAssigns.length > 0 && (
              <div className="rounded-xl border border-gray-200 overflow-hidden mb-3">
                <div className="table-scroll"><table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide text-left">
                      <th className="px-4 py-2.5">Class</th>
                      <th className="px-4 py-2.5">Year</th>
                      <th className="px-4 py-2.5 w-10" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {classAssigns.map((a) => (
                      <tr key={a.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2.5 font-medium text-gray-800">{a.class_name}</td>
                        <td className="px-4 py-2.5 text-gray-500 text-xs">{a.year_label ?? "—"}</td>
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => handleRemoveClassTeacher(a.id)}
                            className="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            )}

            {userId && (
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Assign as class teacher for</label>
                  <select
                    className={INPUT}
                    value={addCTClassId}
                    onChange={(e) => setAddCTClassId(e.target.value ? +e.target.value : "")}
                  >
                    <option value="">Select class…</option>
                    {classes
                      .filter((c) => !ctClassIds.has(c.id))
                      .map((c) => <option key={c.id} value={c.id}>{c.name}</option>)
                    }
                  </select>
                </div>
                <button
                  onClick={handleAddClassTeacher}
                  disabled={!addCTClassId || addingCT}
                  className={`${BTN_SM} bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  <Plus size={13} /> {addingCT ? "Assigning…" : "Assign"}
                </button>
              </div>
            )}
          </section>
        </div>

        <div className="px-6 py-3 border-t border-gray-100 flex justify-end">
          <button onClick={onClose} className="h-9 px-4 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
