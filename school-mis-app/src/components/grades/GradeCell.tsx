const TEXT_COLORS: Record<string, string> = {
  A: "text-emerald-700",
  B: "text-cyan-700",
  C: "text-amber-700",
  D: "text-orange-700",
  F: "text-red-700",
};

interface GradeCellProps {
  score: number | null;
  maxScore?: number;
  letter: string | null;
}

export default function GradeCell({ score, maxScore, letter }: GradeCellProps) {
  if (score === null || !letter) {
    return <span className="text-gray-300 text-xs">—</span>;
  }
  const color = TEXT_COLORS[letter] ?? "text-gray-600";

  return (
    <div className="text-center leading-none">
      <div className={`text-sm font-bold ${color}`}>{letter}</div>
      <div className="text-2xs text-gray-400 mt-0.5">{score}</div>
    </div>
  );
}
