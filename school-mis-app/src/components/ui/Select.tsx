import { clsx } from "clsx";
import { ChevronDown } from "lucide-react";

interface SelectOption {
  value: string | number | null;
  label: string;
}

interface SelectProps {
  value?: string | number | null;
  onChange?: (value: string | number | null) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  error?: string;
}

export default function Select({ value, onChange, options, placeholder, disabled, className, error }: SelectProps) {
  return (
    <div className={clsx("relative", className)}>
      <select
        value={value ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          onChange?.(raw === "" ? null : isNaN(Number(raw)) ? raw : Number(raw));
        }}
        disabled={disabled}
        className={clsx(
          "w-full h-9 pl-3 pr-8 border rounded-lg text-sm appearance-none bg-white",
          "focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent",
          "disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed",
          error ? "border-red-400" : "border-gray-300",
          "text-gray-800"
        )}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={String(o.value)} value={o.value ?? ""}>{o.label}</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}
