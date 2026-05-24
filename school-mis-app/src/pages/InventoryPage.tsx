import { useState, useEffect, useCallback, useRef } from "react";
import { Search, AlertTriangle, Package, Plus, PlusCircle, MinusCircle } from "lucide-react";
import { getInventoryItems, getLowStock, createItem, addStock, issueStock, type InventoryItem } from "@/api/inventory";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ItemDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({ name: "", category: "", quantity: "0", unit: "pcs", min_quantity: "5", location: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name) { setError("Item name is required."); return; }
    setSaving(true);
    setError("");
    try {
      await createItem({
        name:         form.name,
        category:     form.category     || null,
        quantity:     Number(form.quantity)     || 0,
        unit:         form.unit         || "pcs",
        min_quantity: Number(form.min_quantity) || 5,
        location:     form.location     || null,
        description:  form.description  || null,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add item.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Add Inventory Item</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Field label="Item Name *"><input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} /></Field></div>
          <Field label="Category"><input className={INPUT} value={form.category} onChange={(e) => set("category", e.target.value)} /></Field>
          <Field label="Unit"><input className={INPUT} value={form.unit} onChange={(e) => set("unit", e.target.value)} placeholder="pcs, kg, litres…" /></Field>
          <Field label="Initial Qty"><input type="number" min="0" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} /></Field>
          <Field label="Min Qty Alert"><input type="number" min="0" className={INPUT} value={form.min_quantity} onChange={(e) => set("min_quantity", e.target.value)} /></Field>
          <Field label="Location"><input className={INPUT} value={form.location} onChange={(e) => set("location", e.target.value)} /></Field>
          <Field label="Description"><input className={INPUT} value={form.description} onChange={(e) => set("description", e.target.value)} /></Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Add Item"}</Button>
        </div>
      </div>
    </div>
  );
}

function StockDialog({ item, mode, onSave, onClose }: { item: InventoryItem; mode: "add" | "issue"; onSave: () => void; onClose: () => void }) {
  const [quantity, setQuantity] = useState("1");
  const [notes, setNotes]       = useState("");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  const submit = async () => {
    const qty = Number(quantity);
    if (!qty || qty <= 0) { setError("Enter a valid quantity."); return; }
    if (mode === "issue" && qty > item.quantity) { setError(`Only ${item.quantity} ${item.unit} available.`); return; }
    setSaving(true);
    setError("");
    try {
      if (mode === "add") {
        await addStock(item.id, qty, notes);
      } else {
        await issueStock(item.id, qty, notes);
      }
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Operation failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">{mode === "add" ? "Add Stock" : "Issue Stock"}</h2>
        <p className="text-sm text-gray-500 mb-4">{item.name} — current: {item.quantity} {item.unit}</p>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label={`Quantity (${item.unit}) *`}>
            <input type="number" min="1" className={INPUT} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Field label="Notes">
            <input className={INPUT} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional reason…" />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : mode === "add" ? "Add Stock" : "Issue"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function InventoryPage() {
  const [items, setItems]       = useState<InventoryItem[]>([]);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [search, setSearch]     = useState("");
  const [loading, setLoading]   = useState(true);
  const [itemDialog, setItemDialog] = useState(false);
  const [stockDialog, setStockDialog] = useState<{ item: InventoryItem; mode: "add" | "issue" } | null>(null);
  const firstLoad = useRef(true);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    Promise.all([getInventoryItems(search), getLowStock()])
      .then(([all, low]) => { setItems(all); setLowStock(low); })
      .catch(() => {})
      .finally(() => { setLoading(false); firstLoad.current = false; });
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
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setItemDialog(true)}>Add Item</Button>
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
              <th className="px-4 py-3 w-24" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={8} />)
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={8} className="py-16">
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
                      {isLow ? <Badge variant="amber">Low Stock</Badge> : <Badge variant="green">OK</Badge>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setStockDialog({ item, mode: "add" })}
                          title="Add stock"
                          className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                        >
                          <PlusCircle size={14} />
                        </button>
                        <button
                          onClick={() => setStockDialog({ item, mode: "issue" })}
                          title="Issue stock"
                          className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                        >
                          <MinusCircle size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>

      {itemDialog && (
        <ItemDialog onSave={() => { setItemDialog(false); load(); }} onClose={() => setItemDialog(false)} />
      )}
      {stockDialog && (
        <StockDialog
          item={stockDialog.item}
          mode={stockDialog.mode}
          onSave={() => { setStockDialog(null); load(); }}
          onClose={() => setStockDialog(null)}
        />
      )}
    </div>
  );
}
