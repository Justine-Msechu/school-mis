import { useState, useEffect, useCallback } from "react";
import { Search, AlertTriangle, Package } from "lucide-react";
import { getInventoryItems, getLowStock, type InventoryItem } from "@/api/inventory";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

export default function InventoryPage() {
  const [items, setItems]       = useState<InventoryItem[]>([]);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [search, setSearch]     = useState("");
  const [loading, setLoading]   = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getInventoryItems(search), getLowStock()])
      .then(([all, low]) => { setItems(all); setLowStock(low); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [search]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Inventory</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? "Loading…" : `${items.length} items tracked`}
          </p>
        </div>
      </div>

      {!loading && lowStock.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-amber-800 text-sm">Low stock alert</div>
            <div className="text-xs text-amber-700 mt-0.5">
              {lowStock.map((i) => i.name).join(", ")} — below minimum quantity
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search items…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Unit</th>
              <th className="px-4 py-3">Min Qty</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={7} className="py-16">
                    <EmptyState icon={Package} title="No items found" />
                  </td>
                </tr>
              )
              : items.map((item) => {
                const isLow = item.quantity <= item.min_quantity;
                return (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.name}</td>
                    <td className="px-4 py-3 text-gray-500">{item.category || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={isLow ? "font-semibold text-amber-700" : "text-gray-900"}>{item.quantity}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{item.unit}</td>
                    <td className="px-4 py-3 text-gray-400">{item.min_quantity}</td>
                    <td className="px-4 py-3 text-gray-500">{item.location || "—"}</td>
                    <td className="px-4 py-3">
                      {isLow
                        ? <Badge variant="amber">Low Stock</Badge>
                        : <Badge variant="green">OK</Badge>
                      }
                    </td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
