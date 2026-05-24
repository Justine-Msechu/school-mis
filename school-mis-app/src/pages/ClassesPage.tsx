import { useState, useEffect } from "react";
import { LayoutGrid } from "lucide-react";
import { getClassList, type ClassRecord } from "@/api/classes";
import EmptyState from "@/components/ui/EmptyState";

export default function ClassesPage() {
  const [classes, setClasses] = useState<ClassRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getClassList().then(setClasses).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Classes</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {loading ? "Loading…" : `${classes.length} classes`}
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : classes.length === 0 ? (
        <EmptyState icon={LayoutGrid} title="No classes found" description="No classes are configured yet." />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {classes.map((c) => (
            <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="text-lg font-bold text-gray-900">{c.name}</div>
              {c.level && <div className="text-sm text-gray-500 mt-1">Level {c.level}</div>}
              {c.stream && <div className="text-xs text-violet-600 mt-0.5">{c.stream}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
