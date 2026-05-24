import { useState, useEffect } from "react";
import { Bus, Phone, User } from "lucide-react";
import { getRoutes, type Route } from "@/api/transport";
import EmptyState from "@/components/ui/EmptyState";

const fmt = (n: number) => `TZS ${n.toLocaleString()}`;

export default function TransportPage() {
  const [routes, setRoutes]   = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRoutes().then(setRoutes).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Transport</h1>
        <p className="text-sm text-gray-500 mt-0.5">{loading ? "Loading…" : `${routes.length} routes`}</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-36 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : routes.length === 0 ? (
        <EmptyState icon={Bus} title="No routes configured" description="Transport routes will appear here." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((r) => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-9 h-9 bg-violet-100 rounded-lg flex items-center justify-center">
                  <Bus size={18} className="text-violet-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 truncate">{r.name}</div>
                  {r.description && <div className="text-xs text-gray-500 mt-0.5">{r.description}</div>}
                </div>
                {r.fare > 0 && (
                  <div className="text-sm font-bold text-violet-700 whitespace-nowrap">{fmt(r.fare)}</div>
                )}
              </div>
              <div className="mt-3 flex flex-col gap-1">
                {r.vehicle_no && (
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Bus size={11} /> {r.vehicle_no}
                  </div>
                )}
                {r.driver_name && (
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <User size={11} /> {r.driver_name}
                  </div>
                )}
                {r.driver_phone && (
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Phone size={11} /> {r.driver_phone}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
