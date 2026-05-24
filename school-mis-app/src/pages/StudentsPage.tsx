import { useState, useEffect, useCallback } from "react";
import { Search, Plus, UserCheck, UserX } from "lucide-react";
import { getStudents, type Student, type StudentList } from "@/api/students";
import { getClasses, type ClassItem } from "@/api/grades";
import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import { Users } from "lucide-react";

const PAGE_SIZE = 30;

export default function StudentsPage() {
  const [data, setData]       = useState<StudentList | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [search, setSearch]   = useState("");
  const [classId, setClassId] = useState<number | null>(null);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getClasses().then(setClasses).catch(() => {}); }, []);

  const load = useCallback(() => {
    setLoading(true);
    getStudents({ search, class_id: classId ?? undefined, page, per_page: PAGE_SIZE })
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [search, classId, page]);

  useEffect(() => { load(); }, [load]);

  const classOptions = [{ value: null as null, label: "All Classes" }, ...classes.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Students</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.total.toLocaleString()} students enrolled` : "Loading…"}
          </p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />}>Add Student</Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name or admission no…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <Select
          value={classId}
          onChange={(v) => { setClassId(v as number | null); setPage(1); }}
          options={classOptions}
          className="w-44"
        />
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Student</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Adm No</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Class</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Guardian</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Status</th>
              <th className="px-4 py-3 w-24" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : data?.items.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-gray-900">{s.first_name} {s.last_name}</p>
                      <p className="text-2xs text-gray-400">{s.gender}</p>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600 text-xs">{s.admission_no}</td>
                    <td className="px-4 py-2.5 text-gray-600 text-xs">{s.class_name ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <p className="text-xs text-gray-700">{s.guardian_name ?? "—"}</p>
                      <p className="text-2xs text-gray-400">{s.guardian_phone ?? ""}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      {s.is_active
                        ? <Badge variant="green" dot>Active</Badge>
                        : <Badge variant="gray" dot>Inactive</Badge>}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Button variant="ghost" size="xs">Edit</Button>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>

        {!loading && data?.items.length === 0 && (
          <EmptyState icon={Users} title="No students found" description="Try adjusting your search or class filter." />
        )}
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between mt-4 text-xs text-gray-500">
          <span>Page {page} of {data.pages} · {data.total} students</span>
          <div className="flex gap-2">
            <Button variant="outline" size="xs" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <Button variant="outline" size="xs" disabled={page === data.pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
