import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { useSubscriptionStore } from "@/stores/subscriptionStore";

export default function SubscriptionBanner() {
  const warning   = useSubscriptionStore((s) => s.warning);
  const status    = useSubscriptionStore((s) => s.status);
  const [dismissed, setDismissed] = useState(false);

  if (!warning || dismissed) return null;

  const isExpired = status === "expired";

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
      isExpired
        ? "bg-red-600 text-white"
        : "bg-amber-500 text-white"
    }`}>
      <AlertTriangle size={15} className="flex-shrink-0" />
      <span className="flex-1">{warning}</span>
      {!isExpired && (
        <button
          onClick={() => setDismissed(true)}
          className="p-0.5 opacity-70 hover:opacity-100 transition-opacity flex-shrink-0"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
