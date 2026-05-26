import { useState, useEffect } from "react";
import { CheckCircle, Clock } from "lucide-react";
import api from "@/api/client";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

interface PendingGroup {
  subject_id: number;
  exam_id: number;
  class_id: number;
  subject_name: string;
  exam_name: string;
  class_name: string;
  count: number;
}

export default function ApprovalsTab() {
  const [groups, setGroups]   = useState<PendingGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy]       = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api.get("/grades/pending-approval").then((r) => setGroups(r.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const approve = async (g: PendingGroup) => {
    const key = `${g.exam_id}-${g.class_id}-${g.subject_id}`;
    setBusy(key);
    try {
      await api.post("/grades/approve", { exam_id: g.exam_id, class_id: g.class_id, subject_id: g.subject_id });
      load();
    } catch {
      // ignore
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="page-content">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">Pending Approvals</h2>
        <p className="text-sm text-gray-500 mt-0.5">Grade submissions awaiting head-teacher approval</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Exam</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Entries</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : groups.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="py-16">
                    <EmptyState icon={Clock} title="No pending approvals" description="All submitted grades have been approved." />
                  </td>
                </tr>
              )
              : groups.map((g) => {
                const key = `${g.exam_id}-${g.class_id}-${g.subject_id}`;
                return (
                  <tr key={key} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-700">{g.exam_name}</td>
                    <td className="px-4 py-3 text-gray-700">{g.class_name}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{g.subject_name}</td>
                    <td className="px-4 py-3 text-gray-600">{g.count} students</td>
                    <td className="px-4 py-3">
                      <Button
                        variant="primary"
                        size="sm"
                        icon={<CheckCircle size={14} />}
                        onClick={() => approve(g)}
                        disabled={busy === key}
                      >
                        {busy === key ? "Approving…" : "Approve"}
                      </Button>
                    </td>
                  </tr>
                );
              })
            }
          </tbody>
        </table></div>
      </div>
    </div>
  );
}
