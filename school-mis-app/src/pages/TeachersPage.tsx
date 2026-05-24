import { useState, useEffect, useCallback } from "react";
import { Search, Plus, Mail, Phone } from "lucide-react";
import { getTeachers, type Teacher } from "@/api/teachers";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import { Users } from "lucide-react";

export default function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [search, setSearch]     = useState("");
  const [loading, setLoading]   = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getTeachers(search).then(setTeachers).catch(() => {}).finally(() => setLoading(false));
  }, [search]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Teachers</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? "Loading…" : `${teachers.length} staff members`}
          </p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />}>Add Teacher</Button>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, employee no…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Employee No</th>
              <th className="px-4 py-3">Specialization</th>
              <th className="px-4 py-3">Contact</th>
              <th className="px-4 py-3">Qualification</th>
              <th className="px-4 py-3">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : teachers.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={Users} title="No teachers found" description="Try adjusting the search query." />
                  </td>
                </tr>
              )
              : teachers.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{t.first_name} {t.last_name}</div>
                    {t.gender && <div className="text-xs text-gray-400">{t.gender === "M" ? "Male" : "Female"}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.employee_no || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.subject_specialization || "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      {t.phone && (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <Phone size={11} /> {t.phone}
                        </span>
                      )}
                      {t.email && (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <Mail size={11} /> {t.email}
                        </span>
                      )}
                      {!t.phone && !t.email && "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.qualification || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.joining_date || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
