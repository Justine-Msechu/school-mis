import { useState, useEffect } from "react";
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { Package, AlertTriangle, Download, TrendingDown } from "lucide-react";
import {
  getInventoryReportOverview, getInventoryByCategory,
  getInventoryMonthlyMovements, getInventoryTypeDistribution,
  getInventoryLowStockDetail,
  type InventoryOverview, type InventoryCategoryRow,
  type InventoryMovementRow, type InventoryTypeRow,
  type InventoryLowStockRow,
} from "@/api/reports";
import { downloadCSV } from "@/utils/export";

const TZS = (n: number) => `TZS ${Math.round(n ?? 0).toLocaleString()}`;

const PIE_COLORS = ["#7C3AED", "#0891B2", "#059669", "#D97706", "#DC2626", "#DB2777"];

const STAT_COLORS: Record<string, string> = {
  violet:  "bg-violet-50 border-violet-100 text-violet-600 text-violet-700",
  emerald: "bg-emerald-50 border-emerald-100 text-emerald-600 text-emerald-700",
  amber:   "bg-amber-50 border-amber-100 text-amber-600 text-amber-700",
  orange:  "bg-orange-50 border-orange-100 text-orange-600 text-orange-700",
  red:     "bg-red-50 border-red-100 text-red-600 text-red-700",
  blue:    "bg-blue-50 border-blue-100 text-blue-600 text-blue-700",
};

function StatCard({ label, value, sub, color }: {
  label: string; value: string | number; sub?: string; color: keyof typeof STAT_COLORS;
}) {
  const [bg, border, text, val] = STAT_COLORS[color].split(" ");
  return (
    <div className={`rounded-xl border p-4 ${bg} ${border}`}>
      <p className={`text-xs font-medium uppercase tracking-wide ${text}`}>{label}</p>
      <p className={`text-2xl font-bold mt-1 ${val}`}>{String(value)}</p>
      {sub && <p className={`text-xs mt-1 ${text} opacity-70`}>{sub}</p>}
    </div>
  );
}

export default function InventoryTab() {
  const [overview, setOverview]     = useState<InventoryOverview | null>(null);
  const [byCategory, setByCategory] = useState<InventoryCategoryRow[]>([]);
  const [movements, setMovements]   = useState<InventoryMovementRow[]>([]);
  const [typesDist, setTypesDist]   = useState<InventoryTypeRow[]>([]);
  const [lowStock, setLowStock]     = useState<InventoryLowStockRow[]>([]);
  const [loading, setLoading]       = useState(true);
  const [months, setMonths]         = useState(12);

  const load = () => {
    setLoading(true);
    Promise.all([
      getInventoryReportOverview(),
      getInventoryByCategory(),
      getInventoryMonthlyMovements(months),
      getInventoryTypeDistribution(),
      getInventoryLowStockDetail(),
    ]).then(([ov, cat, mov, typ, low]) => {
      setOverview(ov);
      setByCategory(cat);
      setMovements(mov);
      setTypesDist(typ);
      setLowStock(low);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [months]);

  const exportLowStock = () => {
    downloadCSV(
      "Low_Stock_Report",
      ["Item", "Category", "Location", "Current Qty", "Reorder Qty", "Shortage", "Unit Price"],
      lowStock.map((r) => [r.name, r.main_category, r.location, r.quantity, r.reorder_qty, r.shortage, r.unit_price])
    );
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard label="Total Items"       value={overview.total_items}       color="violet" />
          <StatCard label="Stock Value"        value={TZS(overview.stock_value)}  color="emerald" />
          <StatCard label="Pending Requests"   value={overview.pending_requests}  color="orange"
            sub={overview.pending_requests > 0 ? "Awaiting your action" : "All clear"} />
          <StatCard label="Low Stock Items"    value={overview.low_stock_count}   color={overview.low_stock_count > 0 ? "red" : "emerald"}
            sub={overview.low_stock_count > 0 ? "Need restocking" : "Adequately stocked"} />
          <StatCard label="Received Today"     value={`+${overview.today_stock_in}`}  color="blue" />
          <StatCard label="Issued Today"       value={`-${overview.today_issued}`}    color="amber" />
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category breakdown bar chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4">Stock Value by Category</h3>
          {byCategory.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-400">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={byCategory} margin={{ top: 0, right: 10, bottom: 40, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="category"
                  tick={{ fontSize: 10, fill: "#6B7280" }}
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#6B7280" }}
                  tickFormatter={(v) => v >= 1000000 ? `${(v/1000000).toFixed(1)}M` : v >= 1000 ? `${(v/1000).toFixed(0)}K` : String(v)}
                />
                <Tooltip formatter={(v) => TZS(Number(v ?? 0))} />
                <Bar dataKey="total_value" name="Stock Value" fill="#7C3AED" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Type distribution pie chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4">Item Type Distribution</h3>
          {typesDist.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-400">No data</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={typesDist}
                    dataKey="count"
                    nameKey="item_type"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    label={({ name, percent }) =>
                      `${name === "consumable" ? "Consumable" : "Asset"} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {typesDist.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => [`${v} items`, ""]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-1 mt-2">
                {typesDist.map((t, i) => (
                  <div key={t.item_type} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      {t.item_type === "consumable" ? "Consumable" : "Asset"}
                    </span>
                    <span className="font-medium text-gray-700">{t.count} items · {TZS(t.value)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Monthly movements chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-800">Monthly Stock Movements</h3>
          <select
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
            className="h-8 px-2 border border-gray-200 rounded-lg text-xs bg-white focus:outline-none"
          >
            <option value={6}>Last 6 months</option>
            <option value={12}>Last 12 months</option>
            <option value={24}>Last 24 months</option>
          </select>
        </div>
        {movements.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-sm text-gray-400">No movement data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={movements} margin={{ top: 0, right: 10, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#6B7280" }} />
              <YAxis tick={{ fontSize: 10, fill: "#6B7280" }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="received" name="Received"  fill="#059669" radius={[3, 3, 0, 0]} />
              <Bar dataKey="issued"   name="Issued"    fill="#D97706" radius={[3, 3, 0, 0]} />
              <Bar dataKey="adjusted" name="Adjusted"  fill="#0891B2" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Low stock table */}
      {lowStock.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-amber-500" />
              Low Stock Items
              <span className="ml-1 bg-red-100 text-red-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                {lowStock.length}
              </span>
            </h3>
            <button
              onClick={exportLowStock}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <Download size={12} /> Export
            </button>
          </div>
          <div className="table-scroll"><table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                <th className="px-4 py-3">Item</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3 text-right">Current</th>
                <th className="px-4 py-3 text-right">Reorder At</th>
                <th className="px-4 py-3 text-right">Shortage</th>
                <th className="px-4 py-3 text-right">Restock Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lowStock.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                  <td className="px-4 py-3 text-gray-500">{r.main_category || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{r.location || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-bold ${r.quantity === 0 ? "text-red-700" : "text-amber-700"}`}>
                      {r.quantity} {r.unit}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{r.reorder_qty} {r.unit}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-semibold text-red-700 flex items-center justify-end gap-1">
                      <TrendingDown size={11} /> {r.shortage} {r.unit}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 font-medium">
                    {r.unit_price > 0 ? TZS(r.shortage * r.unit_price) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      )}

      {lowStock.length === 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-center gap-3">
          <Package size={20} className="text-emerald-600 shrink-0" />
          <p className="text-sm font-medium text-emerald-700">All items are adequately stocked — no items below reorder level.</p>
        </div>
      )}
    </div>
  );
}
