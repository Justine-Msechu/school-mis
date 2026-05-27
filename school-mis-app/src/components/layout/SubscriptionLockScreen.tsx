import { Lock, PhoneCall } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useSubscriptionStore } from "@/stores/subscriptionStore";

export default function SubscriptionLockScreen() {
  const { user }  = useAuthStore();
  const plan      = useSubscriptionStore((s) => s.plan);
  const daysLeft  = useSubscriptionStore((s) => s.daysLeft);

  const role = user?.role ?? "staff";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/95 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-red-600 px-6 py-6 text-white text-center">
          <Lock size={36} className="mx-auto mb-3" />
          <h2 className="text-xl font-bold">Subscription Expired</h2>
          <p className="text-red-200 text-sm mt-1">
            Access has been suspended until the subscription is renewed.
          </p>
        </div>

        <div className="p-6 space-y-4">
          {/* Info row */}
          <div className="rounded-xl bg-gray-50 border border-gray-200 px-4 py-3 text-sm text-gray-700">
            <p>
              Current plan: <span className="font-semibold capitalize">{plan}</span>
            </p>
            {daysLeft !== null && (
              <p className="mt-0.5 text-red-600 font-medium">
                {daysLeft === 0 ? "Expired today" : `Expired ${Math.abs(daysLeft)} day(s) ago`}
              </p>
            )}
          </div>

          <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-4 text-sm text-amber-900 space-y-2">
            <div className="flex items-start gap-2">
              <PhoneCall size={16} className="mt-0.5 flex-shrink-0 text-amber-600" />
              <p>Contact the platform administrator to renew and restore access.</p>
            </div>
            {role === "admin" && (
              <p className="text-xs text-amber-700 pl-6">
                Go to <strong>Settings → Subscription</strong> to view payment options.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
