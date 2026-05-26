import { useState, useEffect, useCallback } from "react";
import {
  Shield, CheckCircle, Plus, HeartHandshake, Home, Package, AlertTriangle, CheckCheck, Clock,
} from "lucide-react";
import {
  getWelfareRecords, verifyWelfareRecord, getWelfareCategories, createWelfareRecord,
  getCounseling, addCounseling, markFollowUpDone,
  getVisits, addVisit,
  getDistributions, addDistribution,
  getIncidents, addIncident, resolveIncident,
  type WelfareRecord, type CounselingRecord, type VisitRecord,
  type DistributionRecord, type IncidentRecord,
} from "@/api/welfare";
import { getStudents } from "@/api/students";
import { getClassList, getClassStudents, type ClassRecord, type ClassStudent } from "@/api/classes";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "records" | "counseling" | "visits" | "distributions" | "incidents";

const INPUT    = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";
const TEXTAREA = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none";
const SELECT   = INPUT;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

// ── Shared student picker (class → student dropdown) ─────────────────────────
function StudentPicker({
  classId, setClassId, studentId, setStudentId,
  classes, students, loadingStudents,
}: {
  classId: number | ""; setClassId: (v: number | "") => void;
  studentId: number | ""; setStudentId: (v: number | "") => void;
  classes: ClassRecord[]; students: ClassStudent[]; loadingStudents: boolean;
}) {
  return (
    <>
      <Field label="Filter by Class">
        <select className={SELECT} value={classId} onChange={(e) => setClassId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">All Classes</option>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      <Field label="Student *">
        <select className={SELECT} value={studentId} onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : "")} disabled={loadingStudents}>
          <option value="">{loadingStudents ? "Loading…" : `Select student (${students.length})`}</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>{s.first_name} {s.last_name} — {s.admission_no}</option>
          ))}
        </select>
      </Field>
    </>
  );
}

function useStudentPicker() {
  const [classId, setClassId]     = useState<number | "">("");
  const [studentId, setStudentId] = useState<number | "">("");
  const [classes, setClasses]     = useState<ClassRecord[]>([]);
  const [students, setStudents]   = useState<ClassStudent[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(false);

  useEffect(() => {
    getClassList().then(setClasses).catch(() => {});
    loadAll();
  }, []);

  function loadAll() {
    setLoadingStudents(true);
    getStudents({ per_page: 300 })
      .then((r) => setStudents(r.items.map((s) => ({ id: s.id, first_name: s.first_name, last_name: s.last_name, admission_no: s.admission_no, gender: s.gender }))))
      .catch(() => {})
      .finally(() => setLoadingStudents(false));
  }

  useEffect(() => {
    setStudentId("");
    if (classId === "") { loadAll(); return; }
    setLoadingStudents(true);
    getClassStudents(Number(classId))
      .then(setStudents)
      .catch(() => setStudents([]))
      .finally(() => setLoadingStudents(false));
  }, [classId]);

  return { classId, setClassId, studentId, setStudentId, classes, students, loadingStudents };
}

// ── Dialogs ──────────────────────────────────────────────────────────────────

function CounselingDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const picker = useStudentPicker();
  const today  = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ session_date: today, reason: "grief", notes: "", follow_up_date: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const REASONS = [
    { value: "grief",          label: "Grief / Loss" },
    { value: "abuse",          label: "Suspected Abuse" },
    { value: "dropout_risk",   label: "Dropout Risk" },
    { value: "behaviour",      label: "Behaviour Issues" },
    { value: "family_issues",  label: "Family Issues" },
    { value: "other",          label: "Other" },
  ];

  const submit = async () => {
    if (!picker.studentId) { setError("Please select a student."); return; }
    setSaving(true); setError("");
    try {
      await addCounseling({
        student_id:     Number(picker.studentId),
        session_date:   form.session_date,
        reason:         form.reason,
        notes:          form.notes || undefined,
        follow_up_date: form.follow_up_date || null,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DialogShell title="Log Counseling Session" onClose={onClose}>
      {error && <ErrorBanner msg={error} />}
      <div className="space-y-3">
        <StudentPicker {...picker} />
        <Field label="Session Date *">
          <input type="date" className={INPUT} value={form.session_date} onChange={(e) => set("session_date", e.target.value)} />
        </Field>
        <Field label="Reason *">
          <select className={SELECT} value={form.reason} onChange={(e) => set("reason", e.target.value)}>
            {REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </Field>
        <Field label="Notes">
          <textarea className={TEXTAREA} rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </Field>
        <Field label="Follow-up Date (optional)">
          <input type="date" className={INPUT} value={form.follow_up_date} onChange={(e) => set("follow_up_date", e.target.value)} />
        </Field>
      </div>
      <DialogFooter onClose={onClose} onSave={submit} saving={saving} disabled={!picker.studentId} />
    </DialogShell>
  );
}

function VisitDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const picker = useStudentPicker();
  const today  = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ visit_date: today, address_visited: "", findings: "", action_taken: "", next_visit_date: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!picker.studentId) { setError("Please select a student."); return; }
    if (!form.findings.trim()) { setError("Findings are required."); return; }
    setSaving(true); setError("");
    try {
      await addVisit({
        student_id:      Number(picker.studentId),
        visit_date:      form.visit_date,
        address_visited: form.address_visited || undefined,
        findings:        form.findings,
        action_taken:    form.action_taken || undefined,
        next_visit_date: form.next_visit_date || null,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DialogShell title="Log Home Visit" onClose={onClose}>
      {error && <ErrorBanner msg={error} />}
      <div className="space-y-3">
        <StudentPicker {...picker} />
        <Field label="Visit Date *">
          <input type="date" className={INPUT} value={form.visit_date} onChange={(e) => set("visit_date", e.target.value)} />
        </Field>
        <Field label="Address Visited">
          <input className={INPUT} value={form.address_visited} onChange={(e) => set("address_visited", e.target.value)} placeholder="Village / street" />
        </Field>
        <Field label="Findings *">
          <textarea className={TEXTAREA} rows={3} value={form.findings} onChange={(e) => set("findings", e.target.value)} placeholder="What was observed?" />
        </Field>
        <Field label="Action Taken">
          <textarea className={TEXTAREA} rows={2} value={form.action_taken} onChange={(e) => set("action_taken", e.target.value)} placeholder="Any immediate action?" />
        </Field>
        <Field label="Next Visit Date (optional)">
          <input type="date" className={INPUT} value={form.next_visit_date} onChange={(e) => set("next_visit_date", e.target.value)} />
        </Field>
      </div>
      <DialogFooter onClose={onClose} onSave={submit} saving={saving} disabled={!picker.studentId} />
    </DialogShell>
  );
}

const ITEM_LABELS: Record<string, string> = {
  uniform: "Uniform", meals: "Meals", stationery: "Stationery",
  sanitary: "Sanitary Pads", books: "Books", shoes: "Shoes", other: "Other",
};

function DistributionDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const picker = useStudentPicker();
  const today  = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ item_type: "uniform", quantity: "1", unit: "pcs", distribution_date: today, notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!picker.studentId) { setError("Please select a student."); return; }
    setSaving(true); setError("");
    try {
      await addDistribution({
        student_id:        Number(picker.studentId),
        item_type:         form.item_type,
        quantity:          parseFloat(form.quantity) || 1,
        unit:              form.unit || "pcs",
        distribution_date: form.distribution_date,
        notes:             form.notes || undefined,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DialogShell title="Record Distribution" onClose={onClose}>
      {error && <ErrorBanner msg={error} />}
      <div className="space-y-3">
        <StudentPicker {...picker} />
        <Field label="Item *">
          <select className={SELECT} value={form.item_type} onChange={(e) => set("item_type", e.target.value)}>
            {Object.entries(ITEM_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantity">
            <input type="number" min="0.5" step="0.5" className={INPUT} value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
          </Field>
          <Field label="Unit">
            <input className={INPUT} value={form.unit} onChange={(e) => set("unit", e.target.value)} placeholder="pcs / sets / days" />
          </Field>
        </div>
        <Field label="Date *">
          <input type="date" className={INPUT} value={form.distribution_date} onChange={(e) => set("distribution_date", e.target.value)} />
        </Field>
        <Field label="Notes">
          <textarea className={TEXTAREA} rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </Field>
      </div>
      <DialogFooter onClose={onClose} onSave={submit} saving={saving} disabled={!picker.studentId} />
    </DialogShell>
  );
}

const INCIDENT_LABELS: Record<string, string> = {
  absence_risk:     "Chronic Absence Risk",
  suspected_abuse:  "Suspected Abuse",
  behaviour_change: "Sudden Behaviour Change",
  hunger:           "Hunger / Malnutrition",
  loss_of_parent:   "Loss of Parent / Guardian",
  other:            "Other",
};

const INCIDENT_COLORS: Record<string, string> = {
  absence_risk:     "amber",
  suspected_abuse:  "red",
  behaviour_change: "amber",
  hunger:           "orange",
  loss_of_parent:   "violet",
  other:            "gray",
};

function IncidentDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const picker = useStudentPicker();
  const today  = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ incident_type: "absence_risk", reported_date: today, description: "", action_taken: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!picker.studentId) { setError("Please select a student."); return; }
    if (!form.description.trim()) { setError("Description is required."); return; }
    setSaving(true); setError("");
    try {
      await addIncident({
        student_id:    Number(picker.studentId),
        incident_type: form.incident_type,
        reported_date: form.reported_date,
        description:   form.description,
        action_taken:  form.action_taken || undefined,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DialogShell title="Report Welfare Incident" onClose={onClose}>
      {error && <ErrorBanner msg={error} />}
      <div className="space-y-3">
        <StudentPicker {...picker} />
        <Field label="Incident Type *">
          <select className={SELECT} value={form.incident_type} onChange={(e) => set("incident_type", e.target.value)}>
            {Object.entries(INCIDENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        <Field label="Date Reported *">
          <input type="date" className={INPUT} value={form.reported_date} onChange={(e) => set("reported_date", e.target.value)} />
        </Field>
        <Field label="Description *">
          <textarea className={TEXTAREA} rows={3} value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="What happened?" />
        </Field>
        <Field label="Initial Action Taken">
          <textarea className={TEXTAREA} rows={2} value={form.action_taken} onChange={(e) => set("action_taken", e.target.value)} placeholder="Any immediate response?" />
        </Field>
      </div>
      <DialogFooter onClose={onClose} onSave={submit} saving={saving} disabled={!picker.studentId} />
    </DialogShell>
  );
}

// ── Shared dialog shell components ────────────────────────────────────────────
function DialogShell({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">{title}</h2>
        {children}
      </div>
    </div>
  );
}
function ErrorBanner({ msg }: { msg: string }) {
  return <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{msg}</div>;
}
function DialogFooter({ onClose, onSave, saving, disabled }: { onClose: () => void; onSave: () => void; saving: boolean; disabled?: boolean }) {
  return (
    <div className="flex justify-end gap-2 mt-5">
      <Button variant="outline" onClick={onClose}>Cancel</Button>
      <Button variant="primary" onClick={onSave} disabled={saving || disabled}>{saving ? "Saving…" : "Save"}</Button>
    </div>
  );
}

// ── Tab content components ────────────────────────────────────────────────────

const CAT_COLOR: Record<string, string> = {
  orphan: "red", half_orphan: "amber", sponsored: "violet", vulnerable: "gray",
};
const SUPPORT_LABEL: Record<string, string> = {
  full_fees: "Full Fees", partial: "Partial", non_financial: "Non-financial",
};

function RecordsTab() {
  const [records, setRecords] = useState<WelfareRecord[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getWelfareRecords({ category: filter || undefined, limit: 100 })
      .then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => { getWelfareCategories().then(setCategories).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const handleVerify = async (id: number) => { await verifyWelfareRecord(id).catch(() => {}); load(); };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <select className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 w-48"
          value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All Categories</option>
          {categories.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
        </select>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Add Record</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Support</th>
              <th className="px-4 py-3">Sponsor</th>
              <th className="px-4 py-3">Verified</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={6} />) :
              records.length === 0 ? <tr><td colSpan={6} className="py-16"><EmptyState icon={Shield} title="No welfare records" /></td></tr> :
              records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name ?? `#${r.student_id}`}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3"><Badge variant={(CAT_COLOR[r.category] || "gray") as any}>{r.category.replace("_", " ")}</Badge></td>
                  <td className="px-4 py-3 text-xs text-gray-600">{SUPPORT_LABEL[r.support_type] ?? r.support_type}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{r.sponsor_name || r.sponsor_org ? `${r.sponsor_name} ${r.sponsor_org}`.trim() : "—"}</td>
                  <td className="px-4 py-3">{r.verified ? <Badge variant="green">Yes</Badge> : <Badge variant="gray">No</Badge>}</td>
                  <td className="px-4 py-3">
                    {!r.verified && <Button variant="outline" size="sm" icon={<CheckCircle size={13} />} onClick={() => handleVerify(r.id)}>Verify</Button>}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && <WelfareRecordDialog categories={categories.length ? categories : ["orphan", "half_orphan", "sponsored", "vulnerable"]}
        onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />}
    </>
  );
}

// Keep original WelfareDialog for records tab
function WelfareRecordDialog({ categories, onSave, onClose }: { categories: string[]; onSave: () => void; onClose: () => void }) {
  const picker = useStudentPicker();
  const [form, setForm] = useState({ category: categories[0] ?? "orphan", support_type: "non_financial", sponsor_name: "", sponsor_org: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!picker.studentId) { setError("Please select a student."); return; }
    setSaving(true); setError("");
    try {
      await createWelfareRecord({ student_id: Number(picker.studentId), category: form.category, support_type: form.support_type, sponsor_name: form.sponsor_name || undefined, sponsor_org: form.sponsor_org || undefined, notes: form.notes || undefined });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save record.");
    } finally { setSaving(false); }
  };

  return (
    <DialogShell title="Add Welfare Record" onClose={onClose}>
      {error && <ErrorBanner msg={error} />}
      <div className="space-y-3">
        <StudentPicker {...picker} />
        <Field label="Category *">
          <select className={SELECT} value={form.category} onChange={(e) => set("category", e.target.value)}>
            {categories.map((c) => <option key={c} value={c}>{c.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase())}</option>)}
          </select>
        </Field>
        <Field label="Support Type *">
          <select className={SELECT} value={form.support_type} onChange={(e) => set("support_type", e.target.value)}>
            <option value="non_financial">Non-financial</option>
            <option value="full_fees">Full Fees</option>
            <option value="partial">Partial Fees</option>
          </select>
        </Field>
        {form.category === "sponsored" && (
          <>
            <Field label="Sponsor Name"><input className={INPUT} value={form.sponsor_name} onChange={(e) => set("sponsor_name", e.target.value)} /></Field>
            <Field label="Sponsor Organisation"><input className={INPUT} value={form.sponsor_org} onChange={(e) => set("sponsor_org", e.target.value)} /></Field>
          </>
        )}
        <Field label="Notes"><textarea className={TEXTAREA} rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
      </div>
      <DialogFooter onClose={onClose} onSave={submit} saving={saving} disabled={!picker.studentId} />
    </DialogShell>
  );
}

function CounselingTab() {
  const [records, setRecords] = useState<CounselingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getCounseling({ limit: 100 }).then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleFollowUp = async (id: number) => { await markFollowUpDone(id).catch(() => {}); load(); };

  const REASON_LABELS: Record<string, string> = {
    grief: "Grief / Loss", abuse: "Suspected Abuse", dropout_risk: "Dropout Risk",
    behaviour: "Behaviour", family_issues: "Family Issues", other: "Other",
  };

  return (
    <>
      <div className="flex justify-end mb-4">
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Log Session</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3">Counselor</th>
              <th className="px-4 py-3">Follow-up</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={7} />) :
              records.length === 0 ? <tr><td colSpan={7} className="py-16"><EmptyState icon={HeartHandshake} title="No counseling sessions recorded" /></td></tr> :
              records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.session_date}</td>
                  <td className="px-4 py-3"><Badge variant="violet">{REASON_LABELS[r.reason] ?? r.reason}</Badge></td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.counselor_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs">
                    {r.follow_up_date
                      ? r.follow_up_done
                        ? <Badge variant="green">Done</Badge>
                        : <span className="flex items-center gap-1 text-amber-600"><Clock size={12} />{r.follow_up_date}</span>
                      : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate">{r.notes || "—"}</td>
                  <td className="px-4 py-3">
                    {r.follow_up_date && !r.follow_up_done && (
                      <Button variant="outline" size="sm" icon={<CheckCheck size={13} />} onClick={() => handleFollowUp(r.id)}>Done</Button>
                    )}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && <CounselingDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />}
    </>
  );
}

function VisitsTab() {
  const [records, setRecords] = useState<VisitRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getVisits({ limit: 100 }).then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="flex justify-end mb-4">
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Log Visit</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Visit Date</th>
              <th className="px-4 py-3">Address</th>
              <th className="px-4 py-3">Findings</th>
              <th className="px-4 py-3">Action Taken</th>
              <th className="px-4 py-3">Next Visit</th>
              <th className="px-4 py-3">Officer</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={7} />) :
              records.length === 0 ? <tr><td colSpan={7} className="py-16"><EmptyState icon={Home} title="No home visits recorded" /></td></tr> :
              records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.visit_date}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.address_visited || "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-700 max-w-[200px] truncate">{r.findings}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate">{r.action_taken || "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.next_visit_date ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.officer_name ?? "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && <VisitDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />}
    </>
  );
}

function DistributionsTab() {
  const [records, setRecords] = useState<DistributionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog]   = useState(false);
  const [filter, setFilter]   = useState("");

  const load = useCallback(() => {
    setLoading(true);
    getDistributions({ item_type: filter || undefined, limit: 100 }).then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <select className="h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 w-48"
          value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All Items</option>
          {Object.entries(ITEM_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Record Distribution</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Given By</th>
              <th className="px-4 py-3">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={6} />) :
              records.length === 0 ? <tr><td colSpan={6} className="py-16"><EmptyState icon={Package} title="No distributions recorded" /></td></tr> :
              records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3"><Badge variant="blue">{ITEM_LABELS[r.item_type] ?? r.item_type}</Badge></td>
                  <td className="px-4 py-3 text-gray-700">{r.quantity} {r.unit}</td>
                  <td className="px-4 py-3 text-gray-600">{r.distribution_date}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.distributed_by_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate">{r.notes || "—"}</td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && <DistributionDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />}
    </>
  );
}

function IncidentsTab() {
  const [records, setRecords]   = useState<IncidentRecord[]>([]);
  const [loading, setLoading]   = useState(true);
  const [dialog, setDialog]     = useState(false);
  const [showResolved, setShowResolved] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getIncidents({ resolved: showResolved ? undefined : false, limit: 100 })
      .then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, [showResolved]);

  useEffect(() => { load(); }, [load]);

  const handleResolve = async (id: number) => { await resolveIncident(id).catch(() => {}); load(); };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input type="checkbox" className="rounded accent-violet-600" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} />
          Show resolved
        </label>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Report Incident</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Action Taken</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={7} />) :
              records.length === 0 ? <tr><td colSpan={7} className="py-16"><EmptyState icon={AlertTriangle} title="No incidents reported" /></td></tr> :
              records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name}</div>
                    <div className="text-xs text-gray-400">{r.admission_no}</div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={(INCIDENT_COLORS[r.incident_type] || "gray") as any}>
                      {INCIDENT_LABELS[r.incident_type] ?? r.incident_type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.reported_date}</td>
                  <td className="px-4 py-3 text-xs text-gray-700 max-w-[180px] truncate">{r.description}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[140px] truncate">{r.action_taken || "—"}</td>
                  <td className="px-4 py-3">
                    {r.resolved ? <Badge variant="green">Resolved</Badge> : <Badge variant="red">Open</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    {!r.resolved && (
                      <Button variant="outline" size="sm" icon={<CheckCircle size={13} />} onClick={() => handleResolve(r.id)}>Resolve</Button>
                    )}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table></div>
      </div>
      {dialog && <IncidentDialog onSave={() => { setDialog(false); load(); }} onClose={() => setDialog(false)} />}
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "records",       label: "Background",    icon: <Shield size={14} /> },
  { key: "counseling",    label: "Counseling",    icon: <HeartHandshake size={14} /> },
  { key: "visits",        label: "Home Visits",   icon: <Home size={14} /> },
  { key: "distributions", label: "Distributions", icon: <Package size={14} /> },
  { key: "incidents",     label: "Incidents",     icon: <AlertTriangle size={14} /> },
];

export default function WelfarePage() {
  const [tab, setTab] = useState<Tab>("records");

  return (
    <div className="page-content">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Welfare</h1>
        <p className="text-sm text-gray-500 mt-0.5">Student welfare case management</p>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {tab === "records"       && <RecordsTab />}
      {tab === "counseling"    && <CounselingTab />}
      {tab === "visits"        && <VisitsTab />}
      {tab === "distributions" && <DistributionsTab />}
      {tab === "incidents"     && <IncidentsTab />}
    </div>
  );
}
