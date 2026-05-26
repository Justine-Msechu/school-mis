import { useState, useEffect, useCallback, useRef } from "react";
import { Bus, Phone, User, Plus, Edit2, Users, X, UserPlus, Trash2, MapPin } from "lucide-react";
import {
  getRoutes, createRoute, updateRoute, getRouteStudents,
  assignStudent, unassignStudent, type Route,
} from "@/api/transport";
import { getAcademicYears, type AcademicYear } from "@/api/settings";
import { useAuthStore } from "@/stores/authStore";
import api from "@/api/client";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";

const fmt = (n: number) => `TZS ${n.toLocaleString()}`;
const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

// ─── student search ───────────────────────────────────────────────────────────

interface StudentHit {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  class_name: string | null;
}

function StudentSearch({
  value, onChange,
}: {
  value: StudentHit | null;
  onChange: (s: StudentHit | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StudentHit[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = (q: string) => {
    setQuery(q);
    onChange(null);
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const { data } = await api.get("/students", { params: { search: q, limit: 8 } });
        setResults(data.students ?? data ?? []);
        setOpen(true);
      } catch { setResults([]); }
    }, 280);
  };

  const pick = (s: StudentHit) => {
    onChange(s);
    setQuery(`${s.first_name} ${s.last_name} (${s.admission_no})`);
    setOpen(false);
  };

  return (
    <div className="relative">
      <input
        value={value ? `${value.first_name} ${value.last_name} (${value.admission_no})` : query}
        onChange={(e) => search(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder="Search student by name or admission no…"
        className={INPUT}
      />
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {results.map((s) => (
            <button key={s.id} onMouseDown={() => pick(s)}
              className="w-full text-left px-3 py-2 hover:bg-violet-50 text-sm flex justify-between items-center">
              <span className="font-medium">{s.first_name} {s.last_name}</span>
              <span className="text-xs text-gray-400">{s.admission_no} {s.class_name ? `· ${s.class_name}` : ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── route dialog ─────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function RouteDialog({ initial, onSave, onClose }: {
  initial?: Route; onSave: () => void; onClose: () => void;
}) {
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
    setSaving(true); setError("");
    try {
      const payload = {
        name:         form.name.trim(),
        description:  form.description  || "",
        fare:         Number(form.fare) || 0,
        vehicle_no:   form.vehicle_no   || "",
        driver_name:  form.driver_name  || "",
        driver_phone: form.driver_phone || "",
      };
      initial ? await updateRoute(initial.id, payload) : await createRoute(payload);
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save route.");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{initial ? "Edit Route" : "Add Route"}</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Field label="Route Name *">
              <input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} />
            </Field>
          </div>
          <div className="col-span-2">
            <Field label="Description / Stops">
              <input className={INPUT} value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="e.g. Msasani → Mlimani → School" />
            </Field>
          </div>
          <Field label="Fare (TZS/term)">
            <input type="number" min="0" className={INPUT} value={form.fare} onChange={(e) => set("fare", e.target.value)} />
          </Field>
          <Field label="Vehicle No">
            <input className={INPUT} value={form.vehicle_no} onChange={(e) => set("vehicle_no", e.target.value)} placeholder="T123 ABC" />
          </Field>
          <Field label="Driver Name">
            <input className={INPUT} value={form.driver_name} onChange={(e) => set("driver_name", e.target.value)} />
          </Field>
          <Field label="Driver Phone">
            <input className={INPUT} value={form.driver_phone} onChange={(e) => set("driver_phone", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </div>
      </div>
    </div>
  );
}

// ─── students modal ───────────────────────────────────────────────────────────

function StudentsModal({ route, onClose }: { route: Route; onClose: () => void }) {
  const { can } = useAuthStore();
  const [students, setStudents] = useState<any[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [loading, setLoading]   = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<StudentHit | null>(null);
  const [pickupPoint, setPickupPoint] = useState("");
  const [yearId, setYearId] = useState<number | "">("");
  const [assigning, setAssigning] = useState(false);
  const [assignErr, setAssignErr] = useState("");
  const [removing, setRemoving] = useState<number | null>(null);

  const loadStudents = () => {
    setLoading(true);
    getRouteStudents(route.id).then(setStudents).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStudents();
    getAcademicYears().then((yrs) => {
      setYears(yrs);
      const current = yrs.find((y) => y.is_current);
      if (current) setYearId(current.id);
    });
  }, [route.id]);

  const handleAssign = async () => {
    if (!selectedStudent) { setAssignErr("Select a student."); return; }
    if (!yearId)          { setAssignErr("Select an academic year."); return; }
    setAssigning(true); setAssignErr("");
    try {
      await assignStudent({
        student_id:       selectedStudent.id,
        route_id:         route.id,
        academic_year_id: Number(yearId),
        pickup_point:     pickupPoint.trim(),
      });
      setShowForm(false);
      setSelectedStudent(null);
      setPickupPoint("");
      loadStudents();
    } catch (e: any) {
      setAssignErr(e?.response?.data?.detail ?? "Failed to assign student.");
    } finally { setAssigning(false); }
  };

  const handleRemove = async (subId: number) => {
    if (!confirm("Remove this student from the route?")) return;
    setRemoving(subId);
    try { await unassignStudent(subId); loadStudents(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed to remove."); }
    finally { setRemoving(null); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg flex flex-col max-h-[85vh]">
        {/* header */}
        <div className="flex items-center justify-between p-5 border-b shrink-0">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{route.name}</h2>
            <p className="text-xs text-gray-400">
              {students.length} student{students.length !== 1 ? "s" : ""} assigned
            </p>
          </div>
          <div className="flex items-center gap-2">
            {can("transport.assign") && !showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700"
              >
                <UserPlus size={14} /> Assign Student
              </button>
            )}
            <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-600 rounded">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* assign form */}
        {showForm && (
          <div className="p-4 bg-violet-50 border-b shrink-0">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Assign a Student</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Student *</label>
                <StudentSearch value={selectedStudent} onChange={setSelectedStudent} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Academic Year *</label>
                  <select
                    value={yearId}
                    onChange={(e) => setYearId(Number(e.target.value))}
                    className={INPUT}
                  >
                    <option value="">Select year…</option>
                    {years.map((y) => (
                      <option key={y.id} value={y.id}>
                        {y.label}{y.is_current ? " (current)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Pickup Point</label>
                  <input
                    value={pickupPoint}
                    onChange={(e) => setPickupPoint(e.target.value)}
                    placeholder="e.g. Msasani roundabout"
                    className={INPUT}
                  />
                </div>
              </div>
            </div>
            {assignErr && <p className="text-red-600 text-xs mt-2">{assignErr}</p>}
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleAssign}
                disabled={assigning}
                className="px-4 py-1.5 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50"
              >
                {assigning ? "Assigning…" : "Assign"}
              </button>
              <button
                onClick={() => { setShowForm(false); setAssignErr(""); setSelectedStudent(null); setPickupPoint(""); }}
                className="px-4 py-1.5 text-sm border rounded-lg hover:bg-white text-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* student list */}
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="py-10 text-center text-sm text-gray-400">Loading…</div>
          ) : students.length === 0 ? (
            <div className="py-10 text-center">
              <Users size={32} className="mx-auto text-gray-200 mb-2" />
              <p className="text-sm text-gray-400">No students assigned yet.</p>
              {can("transport.assign") && !showForm && (
                <button
                  onClick={() => setShowForm(true)}
                  className="mt-3 text-sm text-violet-600 hover:underline"
                >
                  Assign the first student
                </button>
              )}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase border-b border-gray-100 sticky top-0 bg-white">
                  <th className="px-5 py-3">Student</th>
                  <th className="px-3 py-3">Pickup Point</th>
                  <th className="px-3 py-3 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {students.map((s: any) => (
                  <tr key={s.id} className="hover:bg-gray-50 group">
                    <td className="px-5 py-3">
                      <div className="font-medium text-gray-900">
                        {s.first_name ?? s.student_name?.split(" ")[0]} {s.last_name ?? s.student_name?.split(" ").slice(1).join(" ")}
                      </div>
                      <div className="text-xs text-gray-400">{s.admission_no}</div>
                    </td>
                    <td className="px-3 py-3 text-gray-500 text-xs">
                      {s.pickup_point ? (
                        <span className="flex items-center gap-1">
                          <MapPin size={10} /> {s.pickup_point}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-3">
                      {can("transport.assign") && (
                        <button
                          onClick={() => handleRemove(s.id)}
                          disabled={removing === s.id}
                          className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all disabled:opacity-50"
                          title="Remove from route"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </td>
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

// ─── main page ────────────────────────────────────────────────────────────────

export default function TransportPage() {
  const { can } = useAuthStore();
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
          <p className="text-sm text-gray-500 mt-0.5">{loading ? "Loading…" : `${routes.length} route${routes.length !== 1 ? "s" : ""}`}</p>
        </div>
        {can("transport.manage") && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog("new")}>
            Add Route
          </Button>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : routes.length === 0 ? (
        <EmptyState icon={Bus} title="No routes configured" description="Add transport routes to get started." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((r) => (
            <div key={r.id}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow group">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-9 h-9 bg-violet-100 rounded-lg flex items-center justify-center">
                  <Bus size={18} className="text-violet-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 truncate">{r.name}</div>
                  {r.description && <div className="text-xs text-gray-500 mt-0.5">{r.description}</div>}
                </div>
                {can("transport.manage") && (
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => setDialog(r)}
                      className="p-1 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded"
                    >
                      <Edit2 size={13} />
                    </button>
                  </div>
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
                {r.fare > 0 && (
                  <div className="text-sm font-bold text-violet-700 mt-1">{fmt(r.fare)}/term</div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-gray-100">
                <button
                  onClick={() => setViewing(r)}
                  className="flex items-center gap-1.5 text-xs text-violet-600 hover:text-violet-800 font-medium"
                >
                  <Users size={11} /> View & assign students
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
