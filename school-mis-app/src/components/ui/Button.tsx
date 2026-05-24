import { clsx } from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "outline" | "ghost" | "danger" | "warning" | "success";
type Size    = "xs" | "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary: "bg-violet-600 text-white hover:bg-violet-700 border-transparent shadow-sm",
  outline: "bg-white text-gray-700 border-gray-300 hover:bg-gray-50",
  ghost:   "bg-transparent text-gray-600 border-transparent hover:bg-gray-100",
  danger:  "bg-red-600 text-white hover:bg-red-700 border-transparent shadow-sm",
  warning: "bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200",
  success: "bg-emerald-600 text-white hover:bg-emerald-700 border-transparent shadow-sm",
};

const sizes: Record<Size, string> = {
  xs: "h-7  px-2.5 text-xs  gap-1",
  sm: "h-8  px-3   text-xs  gap-1.5",
  md: "h-9  px-4   text-sm  gap-2",
  lg: "h-10 px-5   text-sm  gap-2",
};

export default function Button({
  variant = "outline",
  size = "md",
  loading,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center font-medium border rounded-lg",
        "transition-colors focus-visible:outline-none focus-visible:ring-2",
        "focus-visible:ring-violet-500 focus-visible:ring-offset-1",
        "disabled:opacity-50 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-r-transparent animate-spin" />
      ) : icon}
      {children}
    </button>
  );
}
