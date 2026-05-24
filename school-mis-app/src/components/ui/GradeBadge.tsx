import { clsx } from "clsx";

const GRADE_STYLES: Record<string, string> = {
  A: "bg-emerald-50 text-emerald-700 border-emerald-200",
  B: "bg-cyan-50 text-cyan-700 border-cyan-200",
  C: "bg-amber-50 text-amber-700 border-amber-200",
  D: "bg-orange-50 text-orange-700 border-orange-200",
  F: "bg-red-50 text-red-700 border-red-200",
};

interface GradeBadgeProps {
  letter: string;
  size?: "sm" | "md" | "lg";
}

export default function GradeBadge({ letter, size = "md" }: GradeBadgeProps) {
  const style = GRADE_STYLES[letter] ?? "bg-gray-50 text-gray-400 border-gray-200";
  return (
    <span
      className={clsx(
        "grade-pill border font-bold",
        style,
        size === "sm" && "text-xs min-w-[22px] h-5",
        size === "md" && "text-sm min-w-[28px] h-6",
        size === "lg" && "text-base min-w-[34px] h-8"
      )}
    >
      {letter || "—"}
    </span>
  );
}
