import { useState, useEffect, useCallback } from "react";
import { Bus, Phone, User, Plus, Edit2, Users, X } from "lucide-react";
import { getRoutes, createRoute, updateRoute, getRouteStudents, type Route } from "@/api/transport";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";

const fmt = (n: number) => `TZS ${n.toLocaleString()}`;
const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function RouteDialog({ initial, onSave, onClose }: { initial?: Route; onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    name:         initial?.name         ?? "",
    description:  initial?.description  ?? "",
    fare:         initial?.fare?.toString() ?? "0",
    vehicle_no:   initial?.vehicle_no   ?? "",
    driver_name:  initial?.driver_name  ?? "",
    driver_phone: initial?.driver_phone ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) { setError("Route name is required."); return; }
    setSaving(true);
    setError("");
    try {
      const payload = {
        name:         form.name.trim(),
        description:  form.description  || "",
        fare:         Number(form.fare) || 0,
        vehicle_no:   form.vehicle_no   || "",
        driver_name:  form.driver_name  || "",
        driver_phone: form.driver_phone || "",
      };
      if (initial) {
        await updateRoute(initial.id, payload);
      } else {
        await createRoute(payload);
      }
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save route.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Route" : "Add Route"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Field label="Route Name *"><input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} /></Field></div>
          <div className="col-span-2"><Field label="Description"><input className={INPUT} value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="Route stops or area…" /></Field></div>
          <Field label="Fare (TZS)"><input type="number" min="0" className={INPUT} value={form.fare} onChange={(e) => set("fare", e.target.value)} /></Field>
          <Field label="Vehicle No"><input className={INPUT} value={form.vehicle_no} onChange={(e) => set("vehicle_no", e.target.value)} placeholder="e.g. T123 ABC" /></Field>
          <Field label="Driver Name"><input className={INPUT} value={form.driver_name} onChange={(e) => set("driver_name", e.target.value)} /></Field>
          <Field label="Driver Phone"><input className={INPUT} value={form.driver_phone} onChange={(e) => set("driver_phone", e.target.value)} /></Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

function StudentsModal({ route, onClose }: { route: Route; onClose: () => void }) {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    getRouteStudents(route.id).then(setStudents).catch(() => {}).finally(() => setLoading(false));
  }, [route.id]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">{route.name} — Students</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-600 rounded"><X size={16} /></button>
        </div>
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="py-8 text-center text-sm text-gray-400">Loading…</div>
          ) : students.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">No students assigned to this route</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase border-b border-gray-100">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Adm. No</th>
                  <th className="pb-2">Pickup</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {students.map((s: any) => (
                  <tr key={s.id}>
                    <td className="py-2 font-medium text-gray-900">{s.first_name} {s.last_name}</td>
                    <td className="py-2 text-gray-500">{s.admission_no}</td>
                    <td className="py-2 text-gray-400">{s.pickup_point || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TransportPage() {
  const [routes, setRoutes]   = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState<Route | null | "new">(null);
  const [viewing, setViewing] = useState<Route | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getRoutes().then(setRoutes).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Transport</h1>
          <p className="text-sm text-gray-500 mt-0.5">{loading ? "Loading…" : `${routes.length} routes`}</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>Add Route</Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : routes.length === 0 ? (
        <EmptyState icon={Bus} title="No routes configured" description="Add transport routes to get started." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((r) => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow group">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-9 h-9 bg-violet-100 rounded-lg flex items-center justify-center">
                  <Bus size={18} className="text-violet-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 truncate">{r.name}</div>
                  {r.description && <div className="text-xs text-gray-500 mt-0.5">{r.description}</div>}
                </div>
                <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => setDialog(r)}
                    className="p-1 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded"
                  >
                    <Edit2 size={13} />
                  </button>
                </div>
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
                {r.fare > 0 && (
                  <div className="text-sm font-bold text-violet-700 mt-1">{fmt(r.fare)}/term</div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-gray-100">
                <button
                  onClick={() => setViewing(r)}
                  className="flex items-center gap-1 text-xs text-violet-600 hover:text-violet-800 font-medium"
                >
                  <Users size={11} /> View students
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {dialog !== null && (
        <RouteDialog
          initial={dialog === "new" ? undefined : dialog}
          onSave={() => { setDialog(null); load(); }}
          onClose={() => setDialog(null)}
        />
      )}
      {viewing && <StudentsModal route={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
