import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { getSubscriptionStatus, type SubscriptionInfo } from "@/api/subscription";
import { useAuthStore } from "@/stores/authStore";

export default function SubscriptionBanner() {
  const { isLoggedIn } = useAuthStore();
  const [info, setInfo] = useState<SubscriptionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) return;
    getSubscriptionStatus().then(setInfo).catch(() => {});
  }, [isLoggedIn]);

  if (!info?.warning || dismissed) return null;

  const isExpired = info.status === "expired";

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
      isExpired
        ? "bg-red-600 text-white"
        : "bg-amber-500 text-white"
    }`}>
      <AlertTriangle size={15} className="flex-shrink-0" />
      <span className="flex-1">{info.warning}</span>
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
