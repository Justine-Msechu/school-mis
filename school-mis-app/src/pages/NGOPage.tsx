import { useState, useEffect, useCallback } from "react";
import {
  Heart, Plus, Edit2, Trash2, Users, Phone, Mail, Globe,
  MapPin, FileText, ChevronDown, ChevronUp, Search,
  CheckCircle, AlertTriangle, Download, X,
} from "lucide-react";
import {
  getNgos, createNgo, updateNgo, deactivateNgo,
  getAllSponsorships, addSponsorship, removeSponsorship, updateSponsorship,
  getNgoReport,
  type Ngo, type Sponsorship, type NgoReport,
} from "@/api/ngo";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import { downloadCSV } from "@/utils/export";

const TZS = (n: number) => `TZS ${Math.round(n ?? 0).toLocaleString()}`;
const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white";
const LABEL = "block text-xs font-medium text-gray-600 mb-1";

type Tab = "ngos" | "beneficiaries" | "report";

const SUPPORT_OPTIONS = [
  { key: "fees",       label: "School Fees" },
  { key: "uniform",    label: "Uniform" },
  { key: "meals",      label: "Meals" },
  { key: "medical",    label: "Medical" },
  { key: "stationery", label: "Stationery" },
  { key: "transport",  label: "Transport" },
];

function SupportBadge({ types }: { types: string | null }) {
  if (!types) return <span className="text-xs text-gray-400">—</span>;
  const list = types.split(",").map((t) => t.trim()).filter(Boolean);
  return (
    <div className="flex flex-wrap gap-1">
      {list.map((t) => {
        const opt = SUPPORT_OPTIONS.find((o) => o.key === t);
        return (
          <span key={t} className="text-xs px-1.5 py-0.5 rounded-full bg-violet-50 text-violet-700 font-medium">
            {opt?.label ?? t}
          </span>
        );
      })}
    </div>
  );
}

// ── NGO form dialog ────────────────────────────────────────────────────────────

function NgoDialog({ initial, onSave, onClose }: {
  initial?: Ngo;
  onSave: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    name:           initial?.name           ?? "",
    contact_person: initial?.contact_person ?? "",
    phone:          initial?.phone          ?? "",
    email:          initial?.email          ?? "",
    address:        initial?.address        ?? "",
    website:        initial?.website        ?? "",
    notes:          initial?.notes          ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) { setError("Organisation name is required."); return; }
    setSaving(true); setError("");
    try {
      initial
        ? await updateNgo(initial.id, form)
        : await createNgo(form);
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card-lg p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          {initial ? "Edit NGO" : "Add NGO Partner"}
        </h2>
        {error && (
          <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={LABEL}>Organisation Name *</label>
            <input className={INPUT} value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. LOHADA Foundation" />
          </div>
          <div>
            <label className={LABEL}>Contact Person</label>
            <input className={INPUT} value={form.contact_person} onChange={(e) => set("contact_person", e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Phone</label>
            <input className={INPUT} value={form.phone} onChange={(e) => set("phone", e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Email</label>
            <input type="email" className={INPUT} value={form.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Website</label>
            <input className={INPUT} value={form.website} onChange={(e) => set("website", e.target.value)} placeholder="https://..." />
          </div>
          <div className="col-span-2">
            <label className={LABEL}>Address</label>
            <input className={INPUT} value={form.address} onChange={(e) => set("address", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={LABEL}>Notes</label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
              rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Add sponsorship dialog ─────────────────────────────────────────────────────

function AddSponsorshipDialog({ ngoId, ngoName, onSave, onClose }: {
  ngoId: number;
  ngoName: string;
  onSave: () => void;
  onClose: () => void;
}) {
  const [search, setSearch]     = useState("");
  const [students, setStudents] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [supportTypes, setSupportTypes] = useState<string[]>([]);
  const [feeAmount, setFeeAmount] = useState("0");
  const [startDate, setStartDate] = useState("");
  const [notes, setNotes]         = useState("");
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState("");

  useEffect(() => {
    if (search.trim().length < 2) { setStudents([]); return; }
    api.get("/students", { params: { search, per_page: 20 } })
      .then(({ data }) => {
        const arr = Array.isArray(data) ? data : (data.items ?? []);
        setStudents(arr);
      })
      .catch(() => {});
  }, [search]);

  const toggleSupport = (key: string) =>
    setSupportTypes((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );

  const submit = async () => {
    if (!selected) { setError("Select a student first."); return; }
    setSaving(true); setError("");
    try {
      await addSponsorship(ngoId, {
        student_id:    selected.id,
        support_types: supportTypes.join(","),
        fee_amount:    Number(feeAmount) || 0,
        start_date:    startDate || undefined,
        notes:         notes || undefined,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add sponsorship.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Add Beneficiary</h2>
        <p className="text-sm text-gray-500 mb-4">Sponsored by <span className="font-medium text-violet-700">{ngoName}</span></p>

        {error && (
          <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
        )}

        {/* student search */}
        <div className="mb-3">
          <label className={LABEL}>Search Student *</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              value={search} onChange={(e) => { setSearch(e.target.value); setSelected(null); }}
              placeholder="Type student name…"
            />
          </div>
          {students.length > 0 && !selected && (
            <div className="mt-1 border border-gray-200 rounded-lg overflow-hidden shadow-sm max-h-40 overflow-y-auto">
              {students.map((s) => (
                <button
                  key={s.id}
                  onClick={() => { setSelected(s); setSearch(s.full_name); setStudents([]); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-violet-50 border-b border-gray-100 last:border-0"
                >
                  <span className="font-medium text-gray-900">{s.full_name}</span>
                  <span className="text-gray-400 ml-2 text-xs">{s.student_id} · {s.class_name ?? "—"}</span>
                </button>
              ))}
            </div>
          )}
          {selected && (
            <div className="mt-1 flex items-center gap-2 px-3 py-2 bg-violet-50 rounded-lg">
              <CheckCircle size={14} className="text-violet-600 shrink-0" />
              <span className="text-sm font-medium text-violet-800">{selected.full_name}</span>
              <span className="text-xs text-violet-500">{selected.class_name}</span>
              <button onClick={() => { setSelected(null); setSearch(""); }} className="ml-auto text-violet-400 hover:text-violet-600">
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* support types */}
        <div className="mb-3">
          <label className={LABEL}>Support Provided</label>
          <div className="flex flex-wrap gap-2">
            {SUPPORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => toggleSupport(opt.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full border-2 transition-colors
                  ${supportTypes.includes(opt.key)
                    ? "border-violet-500 bg-violet-50 text-violet-700"
                    : "border-gray-200 text-gray-500 hover:border-gray-300"}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className={LABEL}>Fee Coverage (TZS/term)</label>
            <input type="number" min="0" className={INPUT} value={feeAmount} onChange={(e) => setFeeAmount(e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Start Date</label>
            <input type="date" className={INPUT} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={LABEL}>Notes</label>
            <input className={INPUT} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>
            {saving ? "Adding…" : "Add Beneficiary"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── NGOs tab ───────────────────────────────────────────────────────────────────

function NgosTab({ onManageStudents }: { onManageStudents: (ngo: Ngo) => void }) {
  const { can } = useAuthStore();
  const [ngos, setNgos]         = useState<Ngo[]>([]);
  const [loading, setLoading]   = useState(true);
  const [editNgo, setEditNgo]   = useState<Ngo | null>(null);
  const [showAdd, setShowAdd]   = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getNgos().then(setNgos).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (ngo: Ngo) => {
    if (!confirm(`Remove "${ngo.name}" from the system?`)) return;
    try { await deactivateNgo(ngo.id); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{ngos.length} partner organisation{ngos.length !== 1 ? "s" : ""}</p>
        {can("ngo.manage") && (
          <Button variant="primary" onClick={() => setShowAdd(true)} icon={<Plus size={14} />}>
            Add NGO
          </Button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : ngos.length === 0 ? (
        <div className="py-20 text-center text-sm text-gray-400">
          <Heart size={40} className="mx-auto text-gray-200 mb-2" />
          No NGO partners registered yet
        </div>
      ) : (
        <div className="space-y-3">
          {ngos.map((ngo) => (
            <div key={ngo.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center shrink-0">
                  <Heart size={18} className="text-violet-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-bold text-gray-900">{ngo.name}</h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium">
                      {ngo.student_count ?? 0} student{(ngo.student_count ?? 0) !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                    {ngo.contact_person && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Users size={10} /> {ngo.contact_person}
                      </span>
                    )}
                    {ngo.phone && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Phone size={10} /> {ngo.phone}
                      </span>
                    )}
                    {ngo.email && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Mail size={10} /> {ngo.email}
                      </span>
                    )}
                    {ngo.website && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Globe size={10} /> {ngo.website}
                      </span>
                    )}
                    {ngo.address && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <MapPin size={10} /> {ngo.address}
                      </span>
                    )}
                  </div>
                  {ngo.notes && (
                    <p className="text-xs text-gray-400 mt-1 truncate">{ngo.notes}</p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => onManageStudents(ngo)}
                    className="px-3 py-1.5 text-xs font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
                  >
                    View Students
                  </button>
                  {can("ngo.manage") && (
                    <>
                      <button
                        onClick={() => setEditNgo(ngo)}
                        className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(ngo)}
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                      >
                        <Trash2 size={14} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd  && <NgoDialog onSave={() => { setShowAdd(false); load(); }} onClose={() => setShowAdd(false)} />}
      {editNgo  && <NgoDialog initial={editNgo} onSave={() => { setEditNgo(null); load(); }} onClose={() => setEditNgo(null)} />}
    </div>
  );
}

// ── Beneficiaries tab ──────────────────────────────────────────────────────────

function BeneficiariesTab() {
  const { can } = useAuthStore();
  const [ngos, setNgos]               = useState<Ngo[]>([]);
  const [sponsorships, setSponsorships] = useState<Sponsorship[]>([]);
  const [filterNgo, setFilterNgo]       = useState<number | "">("");
  const [search, setSearch]             = useState("");
  const [loading, setLoading]           = useState(true);
  const [addTo, setAddTo]               = useState<Ngo | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getNgos(), getAllSponsorships(filterNgo || undefined)])
      .then(([n, s]) => { setNgos(n); setSponsorships(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filterNgo]);

  useEffect(() => { load(); }, [load]);

  const handleRemove = async (sp: Sponsorship) => {
    if (!confirm(`Remove ${sp.full_name} from ${sp.ngo_name}?`)) return;
    try { await removeSponsorship(sp.sponsorship_id); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Failed."); }
  };

  const filtered = sponsorships.filter((sp) => {
    if (!search) return true;
    return sp.full_name.toLowerCase().includes(search.toLowerCase())
      || (sp.admission_no ?? "").toLowerCase().includes(search.toLowerCase());
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-center flex-wrap">
        <div className="relative min-w-48 flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or ID…"
            className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <select
          value={filterNgo} onChange={(e) => setFilterNgo(e.target.value ? Number(e.target.value) : "")}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          <option value="">All NGOs</option>
          {ngos.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
        </select>
        {can("ngo.manage") && ngos.length > 0 && (
          <div className="ml-auto flex gap-2">
            <select
              onChange={(e) => {
                const ngo = ngos.find((n) => n.id === Number(e.target.value));
                if (ngo) setAddTo(ngo);
                e.target.value = "";
              }}
              className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              <option value="">+ Add beneficiary to…</option>
              {ngos.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
            </select>
          </div>
        )}
        {filtered.length > 0 && (
          <button
            onClick={() => downloadCSV(
              "NGO_Beneficiaries",
              ["Student", "Admission No", "Class", "NGO", "Support", "Fee Amount", "Since"],
              filtered.map((sp) => [
                sp.full_name, sp.admission_no, sp.class_name ?? "",
                sp.ngo_name, sp.support_types ?? "", sp.fee_amount,
                sp.start_date ?? "",
              ])
            )}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <Download size={14} /> Export
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="table-scroll"><table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">NGO Partner</th>
              <th className="px-4 py-3">Support Provided</th>
              <th className="px-4 py-3 text-right">Fee Coverage</th>
              <th className="px-4 py-3">Since</th>
              {can("ngo.manage") && <th className="px-4 py-3 w-12" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i}><td colSpan={7} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td></tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-16 text-center text-sm text-gray-400">
                  <Heart size={32} className="mx-auto text-gray-200 mb-2" />
                  No beneficiaries found
                </td>
              </tr>
            ) : filtered.map((sp) => (
              <tr key={sp.sponsorship_id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{sp.full_name}</p>
                  <p className="text-xs text-gray-400">{sp.admission_no}</p>
                </td>
                <td className="px-4 py-3 text-gray-600">{sp.class_name ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-violet-50 text-violet-700">
                    {sp.ngo_name}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <SupportBadge types={sp.support_types} />
                </td>
                <td className="px-4 py-3 text-right text-gray-700 font-medium">
                  {sp.fee_amount > 0 ? TZS(sp.fee_amount) : "—"}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {sp.start_date ?? "—"}
                </td>
                {can("ngo.manage") && (
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleRemove(sp)}
                      title="Remove sponsorship"
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>

      {addTo && (
        <AddSponsorshipDialog
          ngoId={addTo.id}
          ngoName={addTo.name}
          onSave={() => { setAddTo(null); load(); }}
          onClose={() => setAddTo(null)}
        />
      )}
    </div>
  );
}

// ── Report tab ─────────────────────────────────────────────────────────────────

function ReportTab() {
  const [ngos, setNgos]           = useState<Ngo[]>([]);
  const [selectedNgoId, setSelectedNgoId] = useState<number | "">("");
  const [report, setReport]       = useState<NgoReport | null>(null);
  const [loading, setLoading]     = useState(false);

  useEffect(() => { getNgos().then(setNgos).catch(() => {}); }, []);

  useEffect(() => {
    if (!selectedNgoId) { setReport(null); return; }
    setLoading(true);
    getNgoReport(Number(selectedNgoId))
      .then(setReport).catch(() => {}).finally(() => setLoading(false));
  }, [selectedNgoId]);

  const exportReport = () => {
    if (!report) return;
    downloadCSV(
      `NGO_Report_${report.ngo.name}`,
      ["Student", "Adm No", "Class", "Support", "Attendance %", "Total Billed", "Total Paid", "Balance"],
      report.students.map((s) => [
        s.full_name, s.admission_no, s.class_name ?? "",
        s.support_types ?? "", s.attendance_pct,
        s.total_billed, s.total_paid, s.balance,
      ])
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex gap-3 items-center flex-wrap">
        <select
          value={selectedNgoId}
          onChange={(e) => setSelectedNgoId(e.target.value ? Number(e.target.value) : "")}
          className="h-9 px-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 min-w-56"
        >
          <option value="">Select NGO to generate report…</option>
          {ngos.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
        </select>
        {report && (
          <button
            onClick={exportReport}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <Download size={14} /> Export CSV
          </button>
        )}
      </div>

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {report && !loading && (
        <>
          {/* summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label: "Beneficiaries",   value: report.summary.total_beneficiaries, color: "violet" },
              { label: "Avg Attendance",  value: `${report.summary.avg_attendance_pct}%`, color: report.summary.avg_attendance_pct >= 80 ? "emerald" : "amber" },
              { label: "Total Billed",    value: TZS(report.summary.total_billed),   color: "gray" },
              { label: "Total Paid",      value: TZS(report.summary.total_paid),     color: "emerald" },
              { label: "Outstanding",     value: TZS(report.summary.total_balance),  color: report.summary.total_balance > 0 ? "red" : "gray" },
            ].map((s) => (
              <div key={s.label} className={`rounded-xl border p-4
                ${s.color === "violet"  ? "bg-violet-50 border-violet-100" :
                  s.color === "emerald" ? "bg-emerald-50 border-emerald-100" :
                  s.color === "amber"   ? "bg-amber-50 border-amber-100" :
                  s.color === "red"     ? "bg-red-50 border-red-100" :
                  "bg-gray-50 border-gray-100"}`}>
                <p className={`text-xs font-medium uppercase tracking-wide
                  ${s.color === "violet"  ? "text-violet-600" :
                    s.color === "emerald" ? "text-emerald-600" :
                    s.color === "amber"   ? "text-amber-600" :
                    s.color === "red"     ? "text-red-600" :
                    "text-gray-500"}`}>{s.label}</p>
                <p className={`text-xl font-bold mt-1
                  ${s.color === "violet"  ? "text-violet-700" :
                    s.color === "emerald" ? "text-emerald-700" :
                    s.color === "amber"   ? "text-amber-700" :
                    s.color === "red"     ? "text-red-700" :
                    "text-gray-700"}`}>{String(s.value)}</p>
              </div>
            ))}
          </div>

          {/* NGO info strip */}
          <div className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex flex-wrap gap-4 items-center">
            <div className="w-9 h-9 rounded-xl bg-violet-100 flex items-center justify-center shrink-0">
              <Heart size={16} className="text-violet-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900">{report.ngo.name}</p>
              <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-0.5">
                {report.ngo.contact_person && <span className="text-xs text-gray-500">{report.ngo.contact_person}</span>}
                {report.ngo.phone  && <span className="text-xs text-gray-500">{report.ngo.phone}</span>}
                {report.ngo.email  && <span className="text-xs text-gray-500">{report.ngo.email}</span>}
              </div>
            </div>
          </div>

          {/* student table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="table-scroll"><table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
                  <th className="px-4 py-3">Student</th>
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3">Support</th>
                  <th className="px-4 py-3 text-right">Attendance</th>
                  <th className="px-4 py-3 text-right">Billed</th>
                  <th className="px-4 py-3 text-right">Paid</th>
                  <th className="px-4 py-3 text-right">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {report.students.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-sm text-gray-400">
                      No beneficiaries registered for this NGO
                    </td>
                  </tr>
                ) : report.students.map((s) => (
                  <tr key={s.student_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{s.full_name}</p>
                      <p className="text-xs text-gray-400">{s.admission_no}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{s.class_name ?? "—"}</td>
                    <td className="px-4 py-3"><SupportBadge types={s.support_types} /></td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-sm font-semibold
                        ${s.attendance_pct >= 80 ? "text-emerald-700" :
                          s.attendance_pct >= 60 ? "text-amber-700" : "text-red-700"}`}>
                        {s.attendance_pct}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">{TZS(s.total_billed)}</td>
                    <td className="px-4 py-3 text-right text-emerald-700 font-medium">{TZS(s.total_paid)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-semibold ${s.balance > 0 ? "text-red-700" : "text-gray-400"}`}>
                        {TZS(s.balance)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        </>
      )}

      {!selectedNgoId && !loading && (
        <div className="py-24 text-center text-sm text-gray-400">
          <FileText size={40} className="mx-auto text-gray-200 mb-2" />
          Select an NGO above to generate the sponsorship report
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function NGOPage() {
  const [tab, setTab]           = useState<Tab>("ngos");
  const [managingNgo, setManagingNgo] = useState<Ngo | null>(null);

  const tabs: { key: Tab; label: string }[] = [
    { key: "ngos",          label: "Organisations" },
    { key: "beneficiaries", label: "Beneficiaries" },
    { key: "report",        label: "Report" },
  ];

  const handleManageStudents = (ngo: Ngo) => {
    setManagingNgo(ngo);
    setTab("beneficiaries");
  };

  return (
    <div className="page-content">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">NGO Partners</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Partner organisations supporting vulnerable students
        </p>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); if (t.key !== "beneficiaries") setManagingNgo(null); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key
                ? "border-violet-600 text-violet-700"
                : "border-transparent text-gray-500 hover:text-gray-800"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "ngos"          && <NgosTab onManageStudents={handleManageStudents} />}
      {tab === "beneficiaries" && <BeneficiariesTab />}
      {tab === "report"        && <ReportTab />}
    </div>
  );
}
