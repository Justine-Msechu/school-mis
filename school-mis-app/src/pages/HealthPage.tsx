import { useState, useEffect } from "react";
import { Heart, Plus } from "lucide-react";
import { getHealthVisits, type HealthVisit } from "@/api/health";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

export default function HealthPage() {
  const [visits, setVisits]   = useState<HealthVisit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHealthVisits({ limit: 100 }).then(setVisits).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Health</h1>
          <p className="text-sm text-gray-500 mt-0.5">Student health visits and records</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Complaint</th>
              <th className="px-4 py-3">Diagnosis</th>
              <th className="px-4 py-3">Treatment</th>
              <th className="px-4 py-3">Referred</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : visits.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={Heart} title="No health visits recorded" description="Health visits will appear here once logged." />
                  </td>
                </tr>
              )
              : visits.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{v.visit_date}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{v.student_name || `#${v.student_id}`}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.complaint || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.diagnosis || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.treatment || "—"}</td>
                  <td className="px-4 py-3">
                    {v.referred ? <Badge variant="amber">Referred</Badge> : <Badge variant="gray">No</Badge>}
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
