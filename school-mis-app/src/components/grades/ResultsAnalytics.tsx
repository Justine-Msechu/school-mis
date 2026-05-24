import { Users, TrendingUp, CheckCircle } from "lucide-react";
import type { ResultReport } from "@/api/grades";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import DistributionBar from "./DistributionBar";

export default function ResultsAnalytics({ report }: { report: ResultReport }) {
  const graded = report.rows.filter((r) => r.average !== null);
  const avg = graded.length ? graded.reduce((s, r) => s + (r.average ?? 0), 0) / graded.length : 0;
  const passed = graded.filter((r) => r.overall_grade !== "F").length;
  const passRate = graded.length ? Math.round((passed / graded.length) * 100) : 0;

  const gpaVals = report.rows.filter((r) => r.gpa !== null).map((r) => r.gpa as number);
  const classGpa = gpaVals.length ? (gpaVals.reduce((a, b) => a + b, 0) / gpaVals.length).toFixed(2) : null;

  return (
    <div className="grid grid-cols-4 gap-4 mb-5">
      <StatCard
        title="Students"
        value={report.rows.length}
        subtitle={`${report.class.name}`}
        icon={Users}
        color="#7C3AED"
      />
      <StatCard
        title="Class Average"
        value={`${avg.toFixed(1)}%`}
        subtitle={report.exam.name}
        icon={TrendingUp}
        color="#0891B2"
      />
      <StatCard
        title="Pass Rate"
        value={`${passRate}%`}
        subtitle={`${passed} passed · ${graded.length - passed} failed`}
        icon={CheckCircle}
        color={passRate >= 75 ? "#059669" : passRate >= 50 ? "#D97706" : "#DC2626"}
      />

      {/* Distribution card */}
      <Card className="!p-4">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Grade Distribution
          {classGpa && <span className="ml-2 text-violet-600 normal-case">GPA {classGpa}</span>}
        </p>
        <DistributionBar rows={report.rows} />
      </Card>
    </div>
  );
}
