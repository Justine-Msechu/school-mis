import { clsx } from "clsx";

type BadgeVariant = "gray" | "blue" | "green" | "amber" | "red" | "violet" | "cyan" | "orange";

const variants: Record<BadgeVariant, string> = {
  gray:   "bg-gray-100 text-gray-600",
  blue:   "bg-blue-100 text-blue-700",
  green:  "bg-emerald-100 text-emerald-700",
  amber:  "bg-amber-100 text-amber-700",
  red:    "bg-red-100 text-red-700",
  violet: "bg-violet-100 text-violet-700",
  cyan:   "bg-cyan-100 text-cyan-700",
  orange: "bg-orange-100 text-orange-700",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  dot?: boolean;
  className?: string;
}

export default function Badge({ children, variant = "gray", dot, className }: BadgeProps) {
  return (
    <span className={clsx("status-chip", variants[variant], className)}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
