import { useState, useEffect, useCallback, useRef } from "react";
import { Shield, CheckCircle, Plus } from "lucide-react";
import { getWelfareRecords, verifyWelfareRecord, getWelfareCategories, createWelfareRecord, type WelfareRecord } from "@/api/welfare";
import { getStudents } from "@/api/students";
import Badge from "@/components/ui/Badge";
import Select from "@/components/ui/Select";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

const CATEGORY_COLOR: Record<string, string> = {
  orphan:      "red",
  half_orphan: "amber",
  sponsored:   "violet",
  vulnerable:  "gray",
};

const SUPPORT_LABEL: Record<string, string> = {
  full_fees:     "Full Fees",
  partial:       "Partial",
  non_financial: "Non-financial",
};

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

function WelfareDialog({ categories, onSave, onClose }: { categories: string[]; onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    admission_no: "",
    student_id:   null as number | null,
    student_name: "",
    category:     categories[0] ?? "orphan",
    support_type: "non_financial",
    sponsor_name: "",
    sponsor_org:  "",
    notes:        "",
  });
  const [lookupState, setLookupState] = useState<"idle" | "loading" | "found" | "error">("idle");
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

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
    setSaving(true);
    setError("");
    try {
      await createWelfareRecord({
        student_id:   form.student_id,
        category:     form.category,
        support_type: form.support_type,
        sponsor_name: form.sponsor_name || undefined,
        sponsor_org:  form.sponsor_org  || undefined,
        notes:        form.notes        || undefined,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save record.");
    } finally {
      setSaving(false);
    }
  };

  const catOptions = categories.map((c) => ({
    value: c,
    label: c.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase()),
  }));

  const supportOptions = [
    { value: "non_financial", label: "Non-financial" },
    { value: "full_fees",     label: "Full Fees" },
    { value: "partial",       label: "Partial Fees" },
  ];

  const needsSponsor = form.category === "sponsored";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Add Welfare Record</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Student Admission No *">
            <div className="flex gap-2">
              <input
                className={INPUT}
                value={form.admission_no}
                placeholder="e.g. ADM/2024/0001"
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
          <Field label="Category *">
            <Select value={form.category} onChange={(v) => set("category", v as string)} options={catOptions} />
          </Field>
          <Field label="Support Type *">
            <Select value={form.support_type} onChange={(v) => set("support_type", v as string)} options={supportOptions} />
          </Field>
          {needsSponsor && (
            <>
              <Field label="Sponsor Name">
                <input className={INPUT} value={form.sponsor_name} onChange={(e) => set("sponsor_name", e.target.value)} placeholder="Individual or organisation name" />
              </Field>
              <Field label="Sponsor Organisation">
                <input className={INPUT} value={form.sponsor_org} onChange={(e) => set("sponsor_org", e.target.value)} placeholder="Organisation / NGO" />
              </Field>
            </>
          )}
          <Field label="Notes">
            <textarea className={TEXTAREA} rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save Record"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function WelfarePage() {
  const [records, setRecords]       = useState<WelfareRecord[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory]     = useState<string | null>(null);
  const [loading, setLoading]       = useState(true);
  const [dialog, setDialog]         = useState(false);
  const firstLoad = useRef(true);

  const load = useCallback(() => {
    if (firstLoad.current) setLoading(true);
    getWelfareRecords({ category: category ?? undefined, limit: 100 })
      .then(setRecords).catch(() => {}).finally(() => { setLoading(false); firstLoad.current = false; });
  }, [category]);

  useEffect(() => {
    getWelfareCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleVerify = async (id: number) => {
    await verifyWelfareRecord(id).catch(() => {});
    load();
  };

  const catOptions = [
    { value: null as null, label: "All Categories" },
    ...categories.map((c) => ({
      value: c,
      label: c.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    })),
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Welfare</h1>
          <p className="text-sm text-gray-500 mt-0.5">Student welfare support records</p>
        </div>
        <Button variant="primary" icon={<Plus size={15} />} onClick={() => setDialog(true)}>Add Record</Button>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <Select value={category} onChange={(v) => setCategory(v as string | null)} options={catOptions} className="w-48" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Support Type</th>
              <th className="px-4 py-3">Sponsor</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3">Verified</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
              : records.length === 0
              ? (
                <tr>
                  <td colSpan={7} className="py-16">
                    <EmptyState icon={Shield} title="No welfare records" description="Add a record to get started." />
                  </td>
                </tr>
              )
              : records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.student_name || `#${r.student_id}`}</div>
                    {r.admission_no && <div className="text-xs text-gray-400">{r.admission_no}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={(CATEGORY_COLOR[r.category] || "gray") as any}>
                      {r.category.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{SUPPORT_LABEL[r.support_type] ?? r.support_type}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {r.sponsor_name || r.sponsor_org
                      ? <span>{r.sponsor_name}{r.sponsor_name && r.sponsor_org ? " · " : ""}{r.sponsor_org}</span>
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate text-xs">{r.notes || "—"}</td>
                  <td className="px-4 py-3">
                    {r.verified ? <Badge variant="green">Yes</Badge> : <Badge variant="gray">No</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    {!r.verified && (
                      <Button variant="outline" size="sm" icon={<CheckCircle size={13} />} onClick={() => handleVerify(r.id)}>
                        Verify
                      </Button>
                    )}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>

      {dialog && (
        <WelfareDialog
          categories={categories.length ? categories : ["orphan", "half_orphan", "sponsored", "vulnerable"]}
          onSave={() => { setDialog(false); load(); }}
          onClose={() => setDialog(false)}
        />
      )}
    </div>
  );
}
