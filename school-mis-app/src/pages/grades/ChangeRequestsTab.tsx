import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Clock } from "lucide-react";
import api from "@/api/client";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

interface ChangeRequest {
  id: number;
  grade_id: number;
  student_name: string;
  admission_no: string;
  subject_name: string;
  exam_name: string;
  proposed_score: number;
  proposed_max: number;
  reason: string;
  status: string;
  created_at: string;
}

const STATUS_OPTIONS = [
  { value: "pending",  label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function ChangeRequestsTab() {
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [status, setStatus]     = useState("pending");
  const [loading, setLoading]   = useState(true);
  const [busy, setBusy]         = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    api.get("/grades/change-requests", { params: { status } })
      .then((r) => setRequests(r.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [status]);

  const review = async (id: number, action: "approve" | "reject") => {
    setBusy(id);
    try {
      await api.post(`/grades/change-requests/${id}/review`, { action, note: "" });
      load();
    } catch {
      // ignore
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Grade Change Requests</h2>
          <p className="text-sm text-gray-500 mt-0.5">Review requested grade corrections</p>
        </div>
        <Select value={status} onChange={(v) => setStatus(v as string)} options={STATUS_OPTIONS} className="w-36" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Exam / Subject</th>
              <th className="px-4 py-3">Proposed</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : requests.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={Clock} title={`No ${status} requests`} />
                  </td>
                </tr>
              )
              : requests.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    <div>{r.exam_name}</div>
                    <div className="text-xs text-gray-400">{r.subject_name}</div>
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {r.proposed_score}/{r.proposed_max}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{r.reason}</td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{r.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    {r.status === "pending" ? (
                      <div className="flex items-center gap-1.5">
                        <Button
                          variant="primary"
                          size="sm"
                          icon={<CheckCircle size={13} />}
                          onClick={() => review(r.id, "approve")}
                          disabled={busy === r.id}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          icon={<XCircle size={13} />}
                          onClick={() => review(r.id, "reject")}
                          disabled={busy === r.id}
                        >
                          Reject
                        </Button>
                      </div>
                    ) : (
                      <Badge variant={r.status === "approved" ? "green" : "red"}>
                        {r.status}
                      </Badge>
                    )}
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
