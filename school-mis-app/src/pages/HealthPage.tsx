import { useState, useEffect, useCallback, useRef } from "react";
import { Heart, Plus } from "lucide-react";
import { getHealthVisits, recordHealthVisit, type HealthVisit } from "@/api/health";
import { getStudents } from "@/api/students";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";
const TEXTAREA = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function VisitDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    admission_no:  "",
    student_id:    null as number | null,
    student_name:  "",
    visit_date:    new Date().toISOString().slice(0, 10),
    complaint:     "",
    diagnosis:     "",
    treatment:     "",
    prescription:  "",
    follow_up:     "",
    referred:      false,
  });
  const [lookupState, setLookupState] = useState<"idle" | "loading" | "found" | "error">("idle");
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const lookupStudent = async () => {
    if (!form.admission_no.trim()) return;
    setLookupState("loading");
    try {
      const res = await getStudents({ search: form.admission_no.trim(), per_page: 10 });
      const student = res.items.find((s) => s.admission_no === form.admission_no.trim());
      if (student) {
        setForm((f) => ({ ...f, student_id: student.id, student_name: `${student.first_name} ${student.last_name}` }));
        setLookupState("found");
      } else {
        setForm((f) => ({ ...f, student_id: null, student_name: "" }));
        setLookupState("error");
      }
    } catch {
      setLookupState("error");
    }
  };

  const submit = async () => {
    if (!form.student_id) { setError("Please look up a valid student first."); return; }
    if (!form.complaint)  { setError("Complaint is required."); return; }
    setSaving(true);
    setError("");
    try {
      await recordHealthVisit({
        student_id:   form.student_id,
        visit_date:   form.visit_date,
        complaint:    form.complaint,
        diagnosis:    form.diagnosis,
        treatment:    form.treatment,
        prescription: form.prescription,
        follow_up:    form.follow_up || null,
        referred:     form.referred,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to record visit.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Record Health Visit</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Student Admission No *">
            <div className="flex gap-2">
              <input
                className={INPUT}
                value={form.admission_no}
                placeholder="e.g. ADM001"
                onChange={(e) => {
                  setLookupState("idle");
                  setForm((f) => ({ ...f, admission_no: e.target.value, student_id: null, student_name: "" }));
                }}
                onKeyDown={(e) => e.key === "Enter" && lookupStudent()}
              />
              <Button variant="outline" size="sm" onClick={lookupStudent} disabled={lookupState === "loading"}>
                {lookupState === "loading" ? "…" : "Find"}
              </Button>
            </div>
            {lookupState === "found" && <p className="text-xs text-green-600 mt-1">✓ {form.student_name}</p>}
            {lookupState === "error"  && <p className="text-xs text-red-600 mt-1">Student not found</p>}
          </Field>
          <Field label="Visit Date *">
            <input type="date" className={INPUT} value={form.visit_date} onChange={(e) => set("visit_date", e.target.value)} />
          </Field>
          <Field label="Complaint *">
            <textarea className={TEXTAREA} rows={2} value={form.complaint} onChange={(e) => set("complaint", e.target.value)} />
          </Field>
          <Field label="Diagnosis">
            <textarea className={TEXTAREA} rows={2} value={form.diagnosis} onChange={(e) => set("diagnosis", e.target.value)} />
          </Field>
          <Field label="Treatment">
            <textarea className={TEXTAREA} rows={2} value={form.treatment} onChange={(e) => set("treatment", e.target.value)} />
          </Field>
          <Field label="Prescription">
            <input className={INPUT} value={form.prescription} onChange={(e) => set("prescription", e.target.value)} />
          </Field>
          <Field label="Follow-up Date">
            <input type="date" className={INPUT} value={form.follow_up} onChange={(e) => set("follow_up", e.target.value)} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" checked={form.referred} onChange={(e) => set("referred", e.target.checked)} className="rounded" />
            Referred to hospital
          </label>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Record Visit"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function HealthPage() {
  const [visits, setVisits]   = useState<HealthVisit[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);
  const firstLoad = useRef(true);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    getHealthVisits({ limit: 100 }).then(setVisits).catch(() => {}).finally(() => { setLoading(false); firstLoad.current = false; });
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Health</h1>
          <p className="text-sm text-gray-500 mt-0.5">Student health visits and records</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Record Visit</Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Complaint</th>
              <th className="px-4 py-3">Diagnosis</th>
              <th className="px-4 py-3">Treatment</th>
              <th className="px-4 py-3">Referred</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
              : visits.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="py-16">
                    <EmptyState icon={Heart} title="No health visits recorded" description="Health visits will appear here once logged." />
                  </td>
                </tr>
              )
              : visits.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{v.visit_date}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{v.student_name || `#${v.student_id}`}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.complaint || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.diagnosis || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{v.treatment || "—"}</td>
                  <td className="px-4 py-3">
                    {v.referred ? <Badge variant="amber">Referred</Badge> : <Badge variant="gray">No</Badge>}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>

      {dialog && (
        <VisitDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />
      )}
    </div>
  );
}
