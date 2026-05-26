import { useState, useEffect, useCallback } from "react";
import {
  Package, Plus, Search, AlertTriangle, ArrowDownCircle, ArrowUpCircle,
  ClipboardList, History, BarChart2, Edit2, Trash2, CheckCircle, XCircle,
  Download, MapPin, Tag, LayoutDashboard, Activity,
} from "lucide-react";
import {
  getInventoryItems, getInventoryStats, getLowStock,
  createItem, updateItem, deactivateItem,
  receiveStock, issueStock, doStocktake,
  getTransactions, getRequests, createRequest, approveRequest, rejectRequest,
  type InventoryItem, type InventoryStats, type InventoryTransaction, type InventoryRequest,
} from "@/api/inventory";
import { useAuthStore } from "@/stores/authStore";
import { downloadCSV } from "@/utils/export";
import Button from "@/components/ui/Button";

const TZS = (n: number) => `TZS ${Math.round(n ?? 0).toLocaleString()}`;
const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white";
const LABEL = "block text-xs font-medium text-gray-600 mb-1";

type Tab = "overview" | "items" | "receive" | "requests" | "history" | "stocktake";

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  stock_in:  { label: "Stock In",   color: "bg-emerald-50 text-emerald-700" },
  issued:    { label: "Issued",     color: "bg-orange-50 text-orange-700" },
  adjusted:  { label: "Adjusted",  color: "bg-blue-50 text-blue-700" },
  returned:  { label: "Returned",  color: "bg-violet-50 text-violet-700" },
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending:  { label: "Pending",  color: "bg-amber-50 text-amber-700" },
  issued:   { label: "Issued",   color: "bg-emerald-50 text-emerald-700" },
  rejected: { label: "Rejected", color: "bg-red-50 text-red-700" },
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className={LABEL}>{label}</label>
      {children}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_LABELS[status] ?? { label: status, color: "bg-gray-100 text-gray-600" };
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>;
}

// ── Classification data ───────────────────────────────────────────────────────

const MAIN_CATEGORIES: Record<string, string[]> = {
  "Stationery":          ["Writing Materials", "Paper Products", "Filing & Binding", "Art Supplies"],
  "Cleaning & Sanitation": ["Cleaning Agents", "Cleaning Equipment", "Hygiene Products"],
  "Lab & Science":       ["Chemistry", "Biology", "Physics", "General Lab"],
  "Furniture":           ["Chairs", "Desks & Tables", "Storage", "Other Furniture"],
  "IT & Electronics":    ["Computers", "Peripherals", "Audio/Visual", "Other Electronics"],
  "Sports & PE":         ["Ball Games", "Athletics", "Indoor Games", "Other Sports"],
  "Medical & First Aid": ["Medicines", "First Aid Equipment", "PPE"],
  "Books & Learning":    ["Textbooks", "Exercise Books", "Reference Books", "Teaching Aids"],
  "Food & Catering":     ["Food Items", "Utensils", "Catering Equipment"],
  "Other":               ["General"],
};

const ITEM_STATUSES: Record<string, string[]> = {
  consumable: ["available", "low_stock", "out_of_stock", "discontinued"],
  asset:      ["available", "in_use", "under_repair", "disposed", "lost"],
};

const STATUS_DISPLAY: Record<string, { label: string; color: string }> = {
  available:    { label: "Available",    color: "bg-emerald-50 text-emerald-700" },
  low_stock:    { label: "Low Stock",    color: "bg-amber-50 text-amber-700" },
  out_of_stock: { label: "Out of Stock", color: "bg-red-50 text-red-700" },
  discontinued: { label: "Discontinued", color: "bg-gray-100 text-gray-500" },
  in_use:       { label: "In Use",       color: "bg-blue-50 text-blue-700" },
  under_repair: { label: "Under Repair", color: "bg-orange-50 text-orange-700" },
  disposed:     { label: "Disposed",     color: "bg-gray-100 text-gray-500" },
  lost:         { label: "Lost",         color: "bg-red-50 text-red-700" },
};

function ItemStatusBadge({ status }: { status: string }) {
  const s = STATUS_DISPLAY[status] ?? { label: status, color: "bg-gray-100 text-gray-600" };
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>;
}

// ── Item dialog (add / edit) — two-tab form ───────────────────────────────────

function ItemDialog({ initial, onSave, onClose }: {
  initial?: InventoryItem; onSave: () => void; onClose: () => void;
}) {
  const [formTab, setFormTab] = useState<"basic" | "details">("basic");
  const [form, setForm] = useState({
    name:          initial?.name          ?? "",
    item_type:     initial?.item_type     ?? "consumable",
    main_category: initial?.main_category ?? "",
    subcategory:   initial?.subcategory   ?? "",
    unit:          initial?.unit          ?? "pcs",
    quantity:      initial?.quantity?.toString()    ?? "0",
    reorder_qty:   initial?.reorder_qty?.toString() ?? "5",
    unit_price:    initial?.unit_price?.toString()  ?? "0",
    location:      initial?.location      ?? "",
    status:        initial?.status        ?? "available",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const subcategories = MAIN_CATEGORIES[form.main_category] ?? [];
  const statuses = ITEM_STATUSES[form.item_type] ?? ITEM_STATUSES.consumable;

  const submit = async () => {
    if (!form.name.trim()) { setError("Item name is required."); setFormTab("basic"); return; }
    setSaving(true); setError("");
    try {
      const payload = {
        name:          form.name.trim(),
        item_type:     form.item_type,
        main_category: form.main_category || undefined,
        subcategory:   form.subcategory   || undefined,
        unit:          form.unit || "pcs",
        quantity:      Number(form.quantity)    || 0,
        reorder_qty:   Number(form.reorder_qty) || 5,
        unit_price:    Number(form.unit_price)  || 0,
        location:      form.location || undefined,
        status:        form.status,
      };
      initial ? await updateItem(initial.id, payload) : await createItem(payload);
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save item.");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">{initial ? "Edit Item" : "Add Item"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

        {/* form tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-4 w-fit">
          {(["basic", "details"] as const).map((t) => (
            <button key={t} onClick={() => setFormTab(t)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors
                ${formTab === t ? "bg-white text-violet-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
              {t === "basic" ? "Basic Info" : "Details"}
            </button>
          ))}
        </div>

        {formTab === "basic" && (
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field label="Item Name *">
                <input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} />
              </Field>
            </div>

            {/* Item Type toggle */}
            <div className="col-span-2">
              <label className={LABEL}>Item Type *</label>
              <div className="flex gap-2">
                {(["consumable", "asset"] as const).map((t) => (
                  <button key={t} type="button" onClick={() => { set("item_type", t); set("status", ITEM_STATUSES[t][0]); }}
                    className={`flex-1 py-2 text-sm font-medium rounded-lg border-2 transition-colors
                      ${form.item_type === t
                        ? t === "consumable" ? "border-violet-500 bg-violet-50 text-violet-700" : "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-200 text-gray-500 hover:border-gray-300"}`}>
                    {t === "consumable" ? "Consumable" : "Asset / Equipment"}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {form.item_type === "consumable"
                  ? "Gets used up when issued (paper, soap, chalk)"
                  : "Issued and returned, tracked by condition (furniture, equipment)"}
              </p>
            </div>

            <Field label="Main Category">
              <select className={INPUT} value={form.main_category}
                onChange={(e) => { set("main_category", e.target.value); set("subcategory", ""); }}>
                <option value="">— Select —</option>
                {Object.keys(MAIN_CATEGORIES).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Unit">
              <input className={INPUT} value={form.unit} onChange={(e) => set("unit", e.target.value)} placeholder="pcs, kg, reams…" />
            </Field>
            {!initial && (
              <Field label="Opening Qty">
                <input type="number" min="0" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
              </Field>
            )}
            <Field label="Unit Price (TZS)">
              <input type="number" min="0" className={INPUT} value={form.unit_price} onChange={(e) => set("unit_price", e.target.value)} />
            </Field>
          </div>
        )}

        {formTab === "details" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Subcategory">
              <select className={INPUT} value={form.subcategory} onChange={(e) => set("subcategory", e.target.value)}
                disabled={subcategories.length === 0}>
                <option value="">{subcategories.length === 0 ? "Select main category first" : "— Select —"}</option>
                {subcategories.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Status">
              <select className={INPUT} value={form.status} onChange={(e) => set("status", e.target.value)}>
                {statuses.map((s) => (
                  <option key={s} value={s}>{STATUS_DISPLAY[s]?.label ?? s}</option>
                ))}
              </select>
            </Field>
            <div className="col-span-2">
              <Field label="Location">
                <input className={INPUT} value={form.location} onChange={(e) => set("location", e.target.value)}
                  placeholder="e.g. Storeroom A, Shelf B3" />
              </Field>
            </div>
            <Field label="Reorder Level">
              <input type="number" min="0" className={INPUT} value={form.reorder_qty} onChange={(e) => set("reorder_qty", e.target.value)} />
            </Field>
          </div>
        )}

        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

// ── Overview (storekeeper action dashboard) ───────────────────────────────────

function OverviewTab({ onIssue, onReceive, onViewRequests, onViewLowStock }: {
  onIssue:         (item: InventoryItem) => void;
  onReceive:       (item: InventoryItem) => void;
  onViewRequests:  () => void;
  onViewLowStock:  () => void;
}) {
  const { can } = useAuthStore();
  const [stats, setStats]       = useState<InventoryStats | null>(null);
  const [pending, setPending]   = useState<InventoryRequest[]>([]);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [recent, setRecent]     = useState<InventoryTransaction[]>([]);
  const [loading, setLoading]   = useState(true);
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [rejectId, setRejectId]   = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      getInventoryStats(),
      getRequests("pending"),
      getLowStock(),
      getTransactions(undefined, undefined, 10),
    ]).then(([st, pend, low, tx]) => {
      setStats(st); setPending(pend); setLowStock(low); setRecent(tx);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (id: number) => {
    setReviewing(id);
    try { await approveRequest(id); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
    finally { setReviewing(null); }
  };

  const handleReject = async () => {
    if (!rejectId) return;
    try { await rejectRequest(rejectId, rejectNote); setRejectId(null); setRejectNote(""); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
  };

  const canManage = can("inventory.manage");
  const canIssue  = can("inventory.issue");

  return (
    <div className="space-y-6">
      {/* stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Pending Requests",  value: stats?.pending_requests ?? "—",  color: (stats?.pending_requests ?? 0) > 0 ? "orange" : "gray", action: onViewRequests },
          { label: "Low Stock Items",   value: stats?.low_stock_count  ?? "—",  color: (stats?.low_stock_count  ?? 0) > 0 ? "amber"  : "gray", action: onViewLowStock },
          { label: "Total Items",       value: stats?.total_items      ?? "—",  color: "violet", action: null },
          { label: "Today's Movements", value: stats?.today_movements  ?? "—",  color: "emerald", action: null },
        ].map((s) => (
          <div
            key={s.label}
            onClick={() => s.action?.()}
            className={`rounded-xl border p-4 transition-shadow
              ${s.action ? "cursor-pointer hover:shadow-md" : ""}
              ${s.color === "orange"  ? "bg-orange-50 border-orange-100" :
                s.color === "amber"   ? "bg-amber-50 border-amber-100" :
                s.color === "violet"  ? "bg-violet-50 border-violet-100" :
                s.color === "emerald" ? "bg-emerald-50 border-emerald-100" :
                "bg-gray-50 border-gray-100"}`}>
            <p className={`text-xs font-medium uppercase tracking-wide
              ${s.color === "orange"  ? "text-orange-600" :
                s.color === "amber"   ? "text-amber-600" :
                s.color === "violet"  ? "text-violet-600" :
                s.color === "emerald" ? "text-emerald-600" :
                "text-gray-500"}`}>{s.label}</p>
            <p className={`text-2xl font-bold mt-1
              ${s.color === "orange"  ? "text-orange-700" :
                s.color === "amber"   ? "text-amber-700" :
                s.color === "violet"  ? "text-violet-700" :
                s.color === "emerald" ? "text-emerald-700" :
                "text-gray-700"}`}>{String(s.value)}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* pending requests */}
        {canIssue && (
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
                <ClipboardList size={14} className="text-orange-500" />
                Pending Requests
                {pending.length > 0 && (
                  <span className="ml-1 bg-orange-100 text-orange-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {pending.length}
                  </span>
                )}
              </h3>
              <button onClick={onViewRequests} className="text-xs text-violet-600 hover:underline">View all →</button>
            </div>
            {loading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
                ))}
              </div>
            ) : pending.length === 0 ? (
              <div className="py-10 text-center text-sm text-gray-400">
                <CheckCircle size={28} className="mx-auto text-emerald-200 mb-2" />
                No pending requests
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {pending.slice(0, 6).map((r) => (
                  <div key={r.id} className="px-4 py-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{r.item_name}</p>
                      <p className="text-xs text-gray-500">
                        {r.quantity} {r.unit} · {r.requester_name}
                        {r.department ? ` · ${r.department}` : ""}
                      </p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => handleApprove(r.id)}
                        disabled={reviewing === r.id}
                        title="Approve & Issue"
                        className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded disabled:opacity-40"
                      >
                        <CheckCircle size={16} />
                      </button>
                      <button
                        onClick={() => { setRejectId(r.id); setRejectNote(""); }}
                        title="Reject"
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                      >
                        <XCircle size={16} />
                      </button>
                    </div>
                  </div>
                ))}
                {pending.length > 6 && (
                  <div className="px-4 py-2 text-xs text-gray-400 text-center">
                    +{pending.length - 6} more — <button onClick={onViewRequests} className="text-violet-600 hover:underline">view all</button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* low stock alerts */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-amber-500" />
              Low Stock Alerts
            </h3>
            <button onClick={onViewLowStock} className="text-xs text-violet-600 hover:underline">View items →</button>
          </div>
          {loading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : lowStock.length === 0 ? (
            <div className="py-10 text-center text-sm text-gray-400">
              <CheckCircle size={28} className="mx-auto text-emerald-200 mb-2" />
              All items adequately stocked
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {lowStock.slice(0, 6).map((item) => (
                <div key={item.id} className="px-4 py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      {item.main_category || "Uncategorized"}
                      {item.location ? ` · ${item.location}` : ""}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-amber-700">{item.quantity} {item.unit}</p>
                    <p className="text-xs text-gray-400">reorder: {item.reorder_qty}</p>
                  </div>
                  {canManage && (
                    <button
                      onClick={() => onReceive(item)}
                      title="Receive stock"
                      className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded"
                    >
                      <ArrowDownCircle size={15} />
                    </button>
                  )}
                </div>
              ))}
              {lowStock.length > 6 && (
                <div className="px-4 py-2 text-xs text-gray-400 text-center">
                  +{lowStock.length - 6} more items low on stock
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* recent activity */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="flex items-center gap-1.5 px-4 py-3 border-b border-gray-100">
          <Activity size={14} className="text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-800">Recent Activity</h3>
        </div>
        {loading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="py-10 text-center text-sm text-gray-400">No movements yet</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {recent.map((t) => {
              const tl = TYPE_LABELS[t.type] ?? { label: t.type, color: "bg-gray-100 text-gray-600" };
              const qtyColor = t.type === "stock_in" ? "text-emerald-700" : t.type === "issued" ? "text-orange-700" : "text-blue-700";
              return (
                <div key={t.id} className="px-4 py-2.5 flex items-center gap-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${tl.color}`}>{tl.label}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-gray-900">{t.item_name}</span>
                    {(t.supplier || t.issued_to) && (
                      <span className="text-xs text-gray-400 ml-1.5">
                        {t.type === "stock_in" ? `from ${t.supplier}` : `→ ${t.issued_to}`}
                      </span>
                    )}
                  </div>
                  <span className={`text-sm font-bold shrink-0 ${qtyColor}`}>
                    {t.type === "issued" ? "-" : "+"}{t.qty} {t.item_unit}
                  </span>
                  <span className="text-xs text-gray-400 shrink-0 w-20 text-right">
                    {t.created_at.slice(0, 10)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* reject modal */}
      {rejectId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-3">Reject Request</h2>
            <label className={LABEL}>Reason (optional)</label>
            <input className={INPUT} value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} placeholder="Why are you rejecting this?" />
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setRejectId(null)}>Cancel</Button>
              <Button variant="danger" onClick={handleReject}>Reject</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Items tab (full item list — admin/manager view) ────────────────────────────

function DashboardTab({ onAddItem, onReceive, onIssue }: {
  onAddItem: () => void;
  onReceive: (item: InventoryItem) => void;
  onIssue:   (item: InventoryItem) => void;
}) {
  const { can } = useAuthStore();
  const [items, setItems]         = useState<InventoryItem[]>([]);
  const [stats, setStats]         = useState<InventoryStats | null>(null);
  const [search, setSearch]       = useState("");
  const [mainCat, setMainCat]     = useState("");
  const [itemType, setItemType]   = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading]     = useState(true);
  const [editItem, setEditItem]   = useState<InventoryItem | null>(null);

  const load = useCallback(() => {
    Promise.all([getInventoryItems(search, mainCat, itemType, statusFilter), getInventoryStats()])
      .then(([its, st]) => { setItems(its); setStats(st); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [search, mainCat, itemType, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (item: InventoryItem) => {
    if (!confirm(`Deactivate "${item.name}"?`)) return;
    try { await deactivateItem(item.id); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
  };

  return (
    <div className="space-y-5">
      {/* stat cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Total Items",      value: stats.total_items,                     color: "violet" },
            { label: "Stock Value",       value: TZS(stats.stock_value),                color: "emerald" },
            { label: "Low Stock",         value: stats.low_stock_count,                 color: stats.low_stock_count > 0 ? "amber" : "gray" },
            { label: "Pending Requests",  value: stats.pending_requests,                color: stats.pending_requests > 0 ? "orange" : "gray" },
          ].map((s) => (
            <div key={s.label} className={`rounded-xl border p-4
              ${s.color === "violet"  ? "bg-violet-50 border-violet-100" :
                s.color === "emerald" ? "bg-emerald-50 border-emerald-100" :
                s.color === "amber"   ? "bg-amber-50 border-amber-100" :
                s.color === "orange"  ? "bg-orange-50 border-orange-100" :
                "bg-gray-50 border-gray-100"}`}>
              <p className={`text-xs font-medium uppercase tracking-wide
                ${s.color === "violet"  ? "text-violet-600" :
                  s.color === "emerald" ? "text-emerald-600" :
                  s.color === "amber"   ? "text-amber-600" :
                  s.color === "orange"  ? "text-orange-600" :
                  "text-gray-500"}`}>{s.label}</p>
              <p className={`text-2xl font-bold mt-1
                ${s.color === "violet"  ? "text-violet-700" :
                  s.color === "emerald" ? "text-emerald-700" :
                  s.color === "amber"   ? "text-amber-700" :
                  s.color === "orange"  ? "text-orange-700" :
                  "text-gray-700"}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* filters + add button */}
      <div className="flex gap-2 items-center flex-wrap">
        <div className="relative min-w-48 flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search items, location…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
        </div>
        <select value={mainCat} onChange={(e) => setMainCat(e.target.value)}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500">
          <option value="">All Categories</option>
          {Object.keys(MAIN_CATEGORIES).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={itemType} onChange={(e) => setItemType(e.target.value)}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500">
          <option value="">All Types</option>
          <option value="consumable">Consumable</option>
          <option value="asset">Asset</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500">
          <option value="">All Statuses</option>
          {Object.entries(STATUS_DISPLAY).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        {can("inventory.manage") && (
          <button onClick={onAddItem} className="ml-auto flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700">
            <Plus size={14} /> Add Item
          </button>
        )}
      </div>

      {/* items table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3 text-right">Qty</th>
              <th className="px-4 py-3 text-right">Value</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 w-28" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i}><td colSpan={8} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td></tr>
              ))
            ) : items.length === 0 ? (
              <tr><td colSpan={8} className="py-16 text-center text-sm text-gray-400">
                <Package size={32} className="mx-auto text-gray-200 mb-2" />
                No items found
              </td></tr>
            ) : items.map((item) => {
              const isLow = item.quantity <= item.reorder_qty;
              return (
                <tr key={item.id} className="hover:bg-gray-50 group">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{item.name}</div>
                    {item.subcategory && (
                      <div className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                        <Tag size={10} /> {item.subcategory}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full
                      ${item.item_type === "asset" ? "bg-blue-50 text-blue-700" : "bg-violet-50 text-violet-700"}`}>
                      {item.item_type === "asset" ? "Asset" : "Consumable"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{item.main_category || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {item.location ? (
                      <span className="flex items-center gap-1 text-xs">
                        <MapPin size={10} className="text-gray-400 flex-shrink-0" />
                        {item.location}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-semibold ${isLow ? "text-amber-700" : "text-gray-900"}`}>
                      {item.quantity} {item.unit}
                    </span>
                    {isLow && <AlertTriangle size={11} className="inline ml-1 text-amber-500" />}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 font-medium">
                    {item.unit_price > 0 ? TZS(item.quantity * item.unit_price) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <ItemStatusBadge status={item.status || (isLow ? "low_stock" : "available")} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      {can("inventory.manage") && (
                        <>
                          <button onClick={() => onReceive(item)} title="Receive stock" className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded">
                            <ArrowDownCircle size={14} />
                          </button>
                          <button onClick={() => setEditItem(item)} title="Edit item" className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded">
                            <Edit2 size={13} />
                          </button>
                        </>
                      )}
                      {can("inventory.issue") && (
                        <button onClick={() => onIssue(item)} title="Issue stock" className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded">
                          <ArrowUpCircle size={14} />
                        </button>
                      )}
                      {can("inventory.manage") && (
                        <button onClick={() => handleDelete(item)} title="Deactivate" className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded">
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      </div>

      {editItem && (
        <ItemDialog initial={editItem} onSave={() => { setEditItem(null); load(); }} onClose={() => setEditItem(null)} />
      )}
    </div>
  );
}

// ── Receive stock tab ─────────────────────────────────────────────────────────

function ReceiveTab() {
  const [items, setItems]     = useState<InventoryItem[]>([]);
  const [recent, setRecent]   = useState<InventoryTransaction[]>([]);
  const [form, setForm]       = useState({ item_id: "", quantity: "1", supplier: "", unit_cost: "", reference: "", notes: "" });
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState("");
  const [success, setSuccess] = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const load = () => {
    getInventoryItems().then(setItems).catch(() => {});
    getTransactions(undefined, "stock_in", 30).then(setRecent).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!form.item_id) { setError("Select an item."); return; }
    if (!Number(form.quantity) || Number(form.quantity) <= 0) { setError("Enter a valid quantity."); return; }
    setSaving(true); setError(""); setSuccess("");
    try {
      await receiveStock({
        item_id:   Number(form.item_id),
        quantity:  Number(form.quantity),
        supplier:  form.supplier,
        unit_cost: Number(form.unit_cost) || 0,
        reference: form.reference,
        notes:     form.notes,
      });
      setSuccess("Stock received successfully.");
      setForm({ item_id: "", quantity: "1", supplier: "", unit_cost: "", reference: "", notes: "" });
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to receive stock.");
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-xl">
        <h3 className="text-sm font-semibold text-gray-800 mb-4">Receive Delivery</h3>
        {error   && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        {success && <div className="mb-3 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-700">{success}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Field label="Item *">
              <select className={INPUT} value={form.item_id} onChange={(e) => set("item_id", e.target.value)}>
                <option value="">Select item…</option>
                {items.map((i) => <option key={i.id} value={i.id}>{i.name}{i.main_category ? ` — ${i.main_category}` : ""} (stock: {i.quantity} {i.unit})</option>)}
              </select>
            </Field>
          </div>
          <Field label="Quantity *">
            <input type="number" min="1" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
          </Field>
          <Field label="Unit Cost (TZS)">
            <input type="number" min="0" className={INPUT} value={form.unit_cost} onChange={(e) => set("unit_cost", e.target.value)} placeholder="0" />
          </Field>
          <Field label="Supplier">
            <input className={INPUT} value={form.supplier} onChange={(e) => set("supplier", e.target.value)} placeholder="Supplier name" />
          </Field>
          <Field label="Invoice / Reference">
            <input className={INPUT} value={form.reference} onChange={(e) => set("reference", e.target.value)} placeholder="INV-001" />
          </Field>
          <div className="col-span-2">
            <Field label="Notes">
              <input className={INPUT} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
            </Field>
          </div>
        </div>
        <div className="flex justify-end mt-4">
          <Button variant="primary" onClick={submit} disabled={saving} icon={<ArrowDownCircle size={14} />}>
            {saving ? "Saving…" : "Record Receipt"}
          </Button>
        </div>
      </div>

      {/* recent receipts */}
      {recent.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent Receipts</h3>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3 text-right">Unit Cost</th>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3">By</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recent.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{t.created_at.slice(0, 10)}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{t.item_name}</td>
                    <td className="px-4 py-3 text-right text-emerald-700 font-medium">+{t.qty} {t.item_unit}</td>
                    <td className="px-4 py-3 text-gray-500">{t.supplier ?? "—"}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{t.unit_cost ? TZS(t.unit_cost) : "—"}</td>
                    <td className="px-4 py-3 text-gray-400">{t.reference ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{t.recorded_by_name ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Requests tab ──────────────────────────────────────────────────────────────

function RequestsTab() {
  const { can } = useAuthStore();
  const [pending, setPending]   = useState<InventoryRequest[]>([]);
  const [myReqs, setMyReqs]     = useState<InventoryRequest[]>([]);
  const [items, setItems]       = useState<InventoryItem[]>([]);
  const [loading, setLoading]   = useState(true);
  const [sub, setSub]           = useState<"pending" | "all" | "new">("pending");
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [rejectId, setRejectId]   = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  // new request form
  const [form, setForm]       = useState({ item_id: "", quantity: "1", purpose: "", department: "", notes: "" });
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState("");
  const [success, setSuccess] = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const load = () => {
    setLoading(true);
    Promise.all([
      getRequests("pending"),
      getRequests("", true),
      getInventoryItems(),
    ]).then(([p, m, its]) => { setPending(p); setMyReqs(m); setItems(its); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const handleApprove = async (id: number) => {
    setReviewing(id);
    try { await approveRequest(id); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
    finally { setReviewing(null); }
  };

  const handleReject = async () => {
    if (!rejectId) return;
    try { await rejectRequest(rejectId, rejectNote); setRejectId(null); setRejectNote(""); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
  };

  const submitRequest = async () => {
    if (!form.item_id) { setError("Select an item."); return; }
    if (!Number(form.quantity) || Number(form.quantity) <= 0) { setError("Enter a valid quantity."); return; }
    setSaving(true); setError(""); setSuccess("");
    try {
      await createRequest({
        item_id:    Number(form.item_id),
        quantity:   Number(form.quantity),
        purpose:    form.purpose,
        department: form.department,
        notes:      form.notes,
      });
      setSuccess("Request submitted successfully.");
      setForm({ item_id: "", quantity: "1", purpose: "", department: "", notes: "" });
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to submit request.");
    } finally { setSaving(false); }
  };

  const canManage = can("inventory.issue");

  const subTabs = [
    ...(canManage ? [{ key: "pending" as const, label: `Pending (${pending.length})` }] : []),
    ...(canManage ? [{ key: "all"     as const, label: "All Requests" }]                : []),
    { key: "new" as const, label: "New Request" },
  ];
  if (subTabs.length > 0 && !subTabs.find((t) => t.key === sub)) setSub(subTabs[0].key);

  const RequestTable = ({ rows }: { rows: InventoryRequest[] }) => (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="table-scroll"><table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
            <th className="px-4 py-3">Item</th>
            <th className="px-4 py-3 text-right">Qty</th>
            <th className="px-4 py-3">Requested By</th>
            <th className="px-4 py-3">Department</th>
            <th className="px-4 py-3">Purpose</th>
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3">Status</th>
            {canManage && <th className="px-4 py-3 w-28" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <tr key={i}><td colSpan={8} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td></tr>
            ))
          ) : rows.length === 0 ? (
            <tr><td colSpan={8} className="py-12 text-center text-sm text-gray-400">No requests</td></tr>
          ) : rows.map((r) => (
            <tr key={r.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-900">{r.item_name}</td>
              <td className="px-4 py-3 text-right text-gray-700">{r.quantity} {r.unit}</td>
              <td className="px-4 py-3 text-gray-600">{r.requester_name}</td>
              <td className="px-4 py-3 text-gray-500">{r.department ?? "—"}</td>
              <td className="px-4 py-3 text-gray-500">{r.purpose ?? "—"}</td>
              <td className="px-4 py-3 text-gray-400 whitespace-nowrap">{r.created_at.slice(0, 10)}</td>
              <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
              {canManage && (
                <td className="px-4 py-3">
                  {r.status === "pending" && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleApprove(r.id)}
                        disabled={reviewing === r.id}
                        title="Approve & Issue"
                        className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded disabled:opacity-50"
                      >
                        <CheckCircle size={15} />
                      </button>
                      <button
                        onClick={() => { setRejectId(r.id); setRejectNote(""); }}
                        title="Reject"
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                      >
                        <XCircle size={15} />
                      </button>
                    </div>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {subTabs.map((t) => (
          <button key={t.key} onClick={() => setSub(t.key)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors
              ${sub === t.key ? "bg-white text-violet-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {sub === "pending" && <RequestTable rows={pending} />}

      {sub === "all" && <RequestTable rows={myReqs} />}

      {sub === "new" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-xl">
          <h3 className="text-sm font-semibold text-gray-800 mb-1">Request an Item</h3>
          <p className="text-xs text-gray-500 mb-4">Your request will be sent to the storekeeper for review.</p>
          {error   && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
          {success && <div className="mb-3 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-700">{success}</div>}
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field label="Item *">
                <select className={INPUT} value={form.item_id} onChange={(e) => set("item_id", e.target.value)}>
                  <option value="">Select item…</option>
                  {items.map((i) => <option key={i.id} value={i.id}>{i.name} (available: {i.quantity} {i.unit})</option>)}
                </select>
              </Field>
            </div>
            <Field label="Quantity *">
              <input type="number" min="1" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
            </Field>
            <Field label="Department">
              <input className={INPUT} value={form.department} onChange={(e) => set("department", e.target.value)} placeholder="e.g. Science Dept" />
            </Field>
            <div className="col-span-2">
              <Field label="Purpose / Reason">
                <input className={INPUT} value={form.purpose} onChange={(e) => set("purpose", e.target.value)} placeholder="Why do you need this?" />
              </Field>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button variant="primary" onClick={submitRequest} disabled={saving} icon={<ClipboardList size={14} />}>
              {saving ? "Submitting…" : "Submit Request"}
            </Button>
          </div>
        </div>
      )}

      {/* reject modal */}
      {rejectId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-3">Reject Request</h2>
            <Field label="Reason (optional)">
              <input className={INPUT} value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} placeholder="Why are you rejecting this?" />
            </Field>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setRejectId(null)}>Cancel</Button>
              <Button variant="danger" onClick={handleReject}>Reject</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── History tab ───────────────────────────────────────────────────────────────

function HistoryTab() {
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [items, setItems]   = useState<InventoryItem[]>([]);
  const [itemId, setItemId] = useState<number | "">("");
  const [type, setType]     = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getTransactions(itemId || undefined, type, 200)
      .then(setTransactions).catch(() => []).finally(() => setLoading(false));
  }, [itemId, type]);

  useEffect(() => { getInventoryItems().then(setItems).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 items-center flex-wrap">
        <select value={itemId} onChange={(e) => setItemId(e.target.value ? Number(e.target.value) : "")}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white min-w-48">
          <option value="">All Items</option>
          {items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select value={type} onChange={(e) => setType(e.target.value)}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white">
          <option value="">All Types</option>
          <option value="stock_in">Stock In</option>
          <option value="issued">Issued</option>
          <option value="adjusted">Adjusted</option>
          <option value="returned">Returned</option>
        </select>
        {transactions.length > 0 && (
          <button
            onClick={() => downloadCSV("Inventory_History",
              ["Date", "Item", "Type", "Qty", "Supplier / Issued To", "Department", "Reference", "By"],
              transactions.map((t) => [t.created_at.slice(0, 10), t.item_name, t.type, t.qty,
                t.supplier ?? t.issued_to ?? "", t.department ?? "", t.reference ?? "", t.recorded_by_name ?? ""])
            )}
            className="ml-auto flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <Download size={14} /> Export
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3 text-right">Qty</th>
              <th className="px-4 py-3">Supplier / Issued To</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3">By</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}><td colSpan={8} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td></tr>
              ))
            ) : transactions.length === 0 ? (
              <tr><td colSpan={8} className="py-12 text-center text-sm text-gray-400">No transactions found</td></tr>
            ) : transactions.map((t) => {
              const tl = TYPE_LABELS[t.type] ?? { label: t.type, color: "bg-gray-100 text-gray-600" };
              return (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{t.created_at.slice(0, 10)}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{t.item_name}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tl.color}`}>{tl.label}</span>
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${t.type === "issued" ? "text-orange-700" : t.type === "stock_in" ? "text-emerald-700" : "text-blue-700"}`}>
                    {t.type === "issued" ? "-" : "+"}{t.qty} {t.item_unit}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{t.supplier ?? t.issued_to ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-400">{t.department ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{t.notes ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-400">{t.recorded_by_name ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      </div>
    </div>
  );
}

// ── Stocktake tab ─────────────────────────────────────────────────────────────

function StocktakeTab() {
  const [items, setItems]     = useState<InventoryItem[]>([]);
  const [counts, setCounts]   = useState<Record<number, string>>({});
  const [saving, setSaving]   = useState(false);
  const [notes, setNotes]     = useState("");
  const [results, setResults] = useState<any[] | null>(null);
  const [error, setError]     = useState("");

  useEffect(() => {
    getInventoryItems().then((its) => {
      setItems(its);
      const init: Record<number, string> = {};
      its.forEach((i) => { init[i.id] = i.quantity.toString(); });
      setCounts(init);
    }).catch(() => {});
  }, []);

  const submit = async () => {
    setSaving(true); setError(""); setResults(null);
    try {
      const entries = items.map((i) => ({ item_id: i.id, physical_qty: Number(counts[i.id] ?? i.quantity) }));
      const res = await doStocktake(entries, notes);
      setResults(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Stocktake failed.");
    } finally { setSaving(false); }
  };

  if (results) {
    const discrepancies = results.filter((r) => r.diff !== 0);
    return (
      <div className="space-y-5">
        <div className={`p-4 rounded-xl border ${discrepancies.length === 0 ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"}`}>
          <p className={`font-semibold text-sm ${discrepancies.length === 0 ? "text-emerald-700" : "text-amber-700"}`}>
            {discrepancies.length === 0
              ? "Stocktake complete — all counts matched!"
              : `Stocktake complete — ${discrepancies.length} item${discrepancies.length !== 1 ? "s" : ""} adjusted`}
          </p>
        </div>
        {discrepancies.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3 text-right">System Qty</th>
                  <th className="px-4 py-3 text-right">Physical Qty</th>
                  <th className="px-4 py-3 text-right">Difference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {discrepancies.map((r) => (
                  <tr key={r.item_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{r.system_qty}</td>
                    <td className="px-4 py-3 text-right text-gray-900">{r.physical_qty}</td>
                    <td className={`px-4 py-3 text-right font-semibold ${r.diff > 0 ? "text-emerald-700" : "text-red-700"}`}>
                      {r.diff > 0 ? "+" : ""}{r.diff}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        )}
        <button onClick={() => setResults(null)} className="text-sm text-violet-600 hover:underline">← Start new stocktake</button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        Enter the actual physical count for each item. Any differences will be recorded as adjustments.
      </div>
      {error && <div className="px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3 text-right">System Qty</th>
              <th className="px-4 py-3 text-right w-36">Physical Count</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item) => {
              const diff = Number(counts[item.id] ?? item.quantity) - item.quantity;
              return (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{item.name}</td>
                  <td className="px-4 py-3 text-gray-500">{item.main_category || "—"}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{item.quantity} {item.unit}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {diff !== 0 && (
                        <span className={`text-xs font-medium ${diff > 0 ? "text-emerald-600" : "text-red-600"}`}>
                          {diff > 0 ? "+" : ""}{diff}
                        </span>
                      )}
                      <input
                        type="number" min="0"
                        value={counts[item.id] ?? item.quantity}
                        onChange={(e) => setCounts((c) => ({ ...c, [item.id]: e.target.value }))}
                        className="w-24 h-8 px-2 border border-gray-300 rounded-lg text-sm text-right focus:outline-none focus:ring-2 focus:ring-violet-500"
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1 max-w-xs">
          <label className={LABEL}>Notes</label>
          <input className={INPUT} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Stocktake notes…" />
        </div>
        <Button variant="primary" onClick={submit} disabled={saving} icon={<BarChart2 size={14} />}>
          {saving ? "Saving…" : "Apply Stocktake"}
        </Button>
      </div>
    </div>
  );
}

// ── Direct issue dialog ───────────────────────────────────────────────────────

function IssueDialog({ item, onSave, onClose }: { item: InventoryItem; onSave: () => void; onClose: () => void }) {
  const [form, setForm]   = useState({ quantity: "1", issued_to: "", department: "", purpose: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    const qty = Number(form.quantity);
    if (!qty || qty <= 0) { setError("Enter a valid quantity."); return; }
    if (qty > item.quantity) { setError(`Only ${item.quantity} ${item.unit} available.`); return; }
    setSaving(true); setError("");
    try {
      await issueStock({ item_id: item.id, quantity: qty, issued_to: form.issued_to, department: form.department, purpose: form.purpose, notes: form.notes });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed.");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Issue Stock</h2>
        <p className="text-sm text-gray-500 mb-4">{item.name} — available: {item.quantity} {item.unit}</p>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label={`Quantity (${item.unit}) *`}>
            <input type="number" min="1" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
          </Field>
          <Field label="Issued To">
            <input className={INPUT} value={form.issued_to} onChange={(e) => set("issued_to", e.target.value)} placeholder="Name of recipient" />
          </Field>
          <Field label="Department">
            <input className={INPUT} value={form.department} onChange={(e) => set("department", e.target.value)} />
          </Field>
          <Field label="Purpose">
            <input className={INPUT} value={form.purpose} onChange={(e) => set("purpose", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Issuing…" : "Issue"}</Button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function InventoryPage() {
  const { can } = useAuthStore();
  const [tab, setTab]               = useState<Tab>("overview");
  const [showAddItem, setShowAddItem] = useState(false);
  const [receiveItem, setReceiveItem] = useState<InventoryItem | null>(null);
  const [issueItem, setIssueItem]     = useState<InventoryItem | null>(null);
  const [refreshKey, setRefreshKey]   = useState(0);
  const refresh = () => setRefreshKey((k) => k + 1);

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = ([
    { key: "overview",   label: "Overview",         icon: <LayoutDashboard size={14} /> },
    { key: "items",      label: "Items",             icon: <Package size={14} /> },
    { key: "receive",    label: "Receive Stock",     icon: <ArrowDownCircle size={14} /> },
    { key: "requests",   label: "Issue / Requests",  icon: <ClipboardList size={14} /> },
    { key: "history",    label: "History",           icon: <History size={14} /> },
    { key: "stocktake",  label: "Stocktake",         icon: <BarChart2 size={14} /> },
  ] as { key: Tab; label: string; icon: React.ReactNode }[]).filter((t) => {
    if (t.key === "receive"   && !can("inventory.manage")) return false;
    if (t.key === "stocktake" && !can("inventory.manage")) return false;
    return true;
  });

  return (
    <div className="page-content">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Inventory</h1>
        <p className="text-sm text-gray-500 mt-0.5">Stock management and issue tracking</p>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <OverviewTab
          key={refreshKey}
          onIssue={(item) => setIssueItem(item)}
          onReceive={(item) => { setReceiveItem(item); setTab("receive"); }}
          onViewRequests={() => setTab("requests")}
          onViewLowStock={() => setTab("items")}
        />
      )}
      {tab === "items" && (
        <DashboardTab
          key={refreshKey}
          onAddItem={() => setShowAddItem(true)}
          onReceive={(item) => { setReceiveItem(item); setTab("receive"); }}
          onIssue={(item) => setIssueItem(item)}
        />
      )}
      {tab === "receive"   && <ReceiveTab key={refreshKey} />}
      {tab === "requests"  && <RequestsTab key={refreshKey} />}
      {tab === "history"   && <HistoryTab />}
      {tab === "stocktake" && <StocktakeTab />}

      {showAddItem && (
        <ItemDialog onSave={() => { setShowAddItem(false); refresh(); }} onClose={() => setShowAddItem(false)} />
      )}
      {receiveItem && tab !== "receive" && (
        <IssueDialog item={receiveItem} onSave={() => { setReceiveItem(null); refresh(); }} onClose={() => setReceiveItem(null)} />
      )}
      {issueItem && (
        <IssueDialog item={issueItem} onSave={() => { setIssueItem(null); refresh(); }} onClose={() => setIssueItem(null)} />
      )}
    </div>
  );
}
