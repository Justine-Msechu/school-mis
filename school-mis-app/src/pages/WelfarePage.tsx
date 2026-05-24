import { useState, useEffect, useCallback } from "react";
import { Shield, CheckCircle } from "lucide-react";
import { getWelfareRecords, verifyWelfareRecord, getWelfareCategories, type WelfareRecord } from "@/api/welfare";
import Badge from "@/components/ui/Badge";
import Select from "@/components/ui/Select";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import Button from "@/components/ui/Button";

const CATEGORY_COLOR: Record<string, string> = {
  disciplinary: "red",
  counseling:   "amber",
  achievement:  "green",
  support:      "gray",
};

export default function WelfarePage() {
  const [records, setRecords]       = useState<WelfareRecord[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory]     = useState<string | null>(null);
  const [loading, setLoading]       = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getWelfareRecords({ category: category ?? undefined, limit: 100 })
      .then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    getWelfareCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleVerify = async (id: number) => {
    await verifyWelfareRecord(id).catch(() => {});
    load();
  };

  const catOptions = [
    { value: null as null, label: "All Categories" },
    ...categories.map((c) => ({ value: c, label: c.charAt(0).toUpperCase() + c.slice(1) })),
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Welfare</h1>
          <p className="text-sm text-gray-500 mt-0.5">Student welfare and incident records</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <Select value={category} onChange={(v) => setCategory(v as string | null)} options={catOptions} className="w-48" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Action Taken</th>
              <th className="px-4 py-3">Verified</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
              : records.length === 0
              ? (
                <tr>
                  <td colSpan={7} className="py-16">
                    <EmptyState icon={Shield} title="No welfare records" />
                  </td>
                </tr>
              )
              : records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name || `#${r.student_id}`}</div>
                    {r.admission_no && <div className="text-xs text-gray-400">{r.admission_no}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={(CATEGORY_COLOR[r.category] || "gray") as any}>
                      {r.category}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{r.incident_date}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{r.description}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[160px] truncate">{r.action_taken || "—"}</td>
                  <td className="px-4 py-3">
                    {r.is_verified ? <Badge variant="green">Yes</Badge> : <Badge variant="gray">No</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    {!r.is_verified && (
                      <Button variant="outline" size="sm" icon={<CheckCircle size={13} />} onClick={() => handleVerify(r.id)}>
                        Verify
                      </Button>
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
