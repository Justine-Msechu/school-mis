import type { ResultRow } from "@/api/grades";

const GRADE_COLORS: Record<string, { bg: string; text: string }> = {
  A: { bg: "bg-emerald-500", text: "text-emerald-700" },
  B: { bg: "bg-cyan-500",    text: "text-cyan-700" },
  C: { bg: "bg-amber-500",   text: "text-amber-700" },
  D: { bg: "bg-orange-500",  text: "text-orange-700" },
  F: { bg: "bg-red-500",     text: "text-red-700" },
};

export default function DistributionBar({ rows }: { rows: ResultRow[] }) {
  const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, F: 0 };
  rows.forEach((r) => {
    if (r.overall_grade in counts) counts[r.overall_grade]++;
  });
  const total = rows.length || 1;

  return (
    <div className="space-y-2">
      {Object.entries(counts).map(([grade, count]) => {
        const pct = (count / total) * 100;
        const { bg, text } = GRADE_COLORS[grade];
        return (
          <div key={grade} className="flex items-center gap-2">
            <span className={`w-4 text-xs font-bold ${text}`}>{grade}</span>
            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${bg}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-4 text-xs text-gray-500 text-right">{count}</span>
          </div>
        );
      })}
    </div>
  );
}
