import { useState, useEffect, useCallback } from "react";
import { Plus, BookOpen } from "lucide-react";
import api from "@/api/client";
import { getClasses, type ClassItem } from "@/api/grades";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

interface Assignment {
  id: number;
  class_id: number;
  subject_id: number;
  title: string;
  instructions: string;
  deadline: string;
  max_points: number;
  class_name: string;
  subject_name: string;
}

export default function HomeworkTab() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [classes, setClasses]         = useState<ClassItem[]>([]);
  const [classId, setClassId]         = useState<number | null>(null);
  const [loading, setLoading]         = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api.get("/grades/homework", { params: { class_id: classId } })
      .then((r) => setAssignments(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [classId]);

  useEffect(() => { getClasses().then(setClasses).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const classOptions = [{ value: null as null, label: "All Classes" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Homework</h2>
          <p className="text-sm text-gray-500 mt-0.5">Assignments and deadlines</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <Select value={classId} onChange={(v) => setClassId(v as number | null)} options={classOptions} className="w-48" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Deadline</th>
              <th className="px-4 py-3">Max Points</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : assignments.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="py-16">
                    <EmptyState icon={BookOpen} title="No assignments" description="Homework assignments will appear here." />
                  </td>
                </tr>
              )
              : assignments.map((a) => {
                const isPast = new Date(a.deadline) < new Date();
                return (
                  <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{a.title}</td>
                    <td className="px-4 py-3 text-gray-600">{a.class_name}</td>
                    <td className="px-4 py-3 text-gray-600">{a.subject_name}</td>
                    <td className={`px-4 py-3 ${isPast ? "text-red-600 font-medium" : "text-gray-600"}`}>
                      {a.deadline}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.max_points}</td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
