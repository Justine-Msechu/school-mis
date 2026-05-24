import { clsx } from "clsx";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; label: string };
  icon?: LucideIcon;
  color?: string;
  className?: string;
}

const trendColor = (v: number) => (v >= 0 ? "text-emerald-600" : "text-red-500");
const trendSign  = (v: number) => (v >= 0 ? "↑" : "↓");

export default function StatCard({ title, value, subtitle, trend, icon: Icon, color = "#7C3AED", className }: StatCardProps) {
  const iconBg = color + "18"; // ~10% opacity hex approximation

  return (
    <div className={clsx("bg-white border border-gray-200 rounded-xl shadow-sm p-5", className)}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
        {Icon && (
          <span className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-lg" style={{ background: iconBg }}>
            <Icon size={18} style={{ color }} />
          </span>
        )}
      </div>

      <p className="mt-2 text-3xl font-bold" style={{ color }}>{value}</p>

      {trend && (
        <p className={clsx("mt-1 text-xs font-medium", trendColor(trend.value))}>
          {trendSign(trend.value)} {Math.abs(trend.value)}% {trend.label}
        </p>
      )}

      {subtitle && !trend && (
        <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
      )}
    </div>
  );
}
