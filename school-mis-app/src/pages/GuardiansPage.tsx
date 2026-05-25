import { useEffect, useRef, useState } from "react";
import { UserPlus, Phone, Mail } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import SearchInput from "@/components/ui/SearchInput";
import Modal from "@/components/ui/Modal";
import FormField from "@/components/ui/FormField";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { DataTable, type Column } from "@/components/data/DataTable";
import { useToast } from "@/components/ui/Toast";
import {
  listGuardians, createGuardian, updateGuardian, deleteGuardian,
  getGuardian, type Guardian,
} from "@/api/guardians";

export default function GuardiansPage() {
  const toast = useToast();
  const firstLoad = useRef(true);
  const [loading, setLoading] = useState(true);
  const [guardians, setGuardians] = useState<Guardian[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Guardian | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Partial<Guardian>>({});

  const load = (q = search) => {
    if (firstLoad.current) { firstLoad.current = false; setLoading(true); }
    listGuardians(q).then(setGuardians).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setTimeout(() => load(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const openCreate = () => { setSelected(null); setForm({}); setFormOpen(true); };
  const openEdit = async (g: Guardian) => {
    const full = await getGuardian(g.id);
    setSelected(full);
    setForm(full);
    setFormOpen(true);
  };
  const openDelete = (g: Guardian) => { setSelected(g); setDeleteOpen(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (selected) {
        await updateGuardian(selected.id, form);
        toast.success("Guardian updated");
      } else {
        await createGuardian(form);
        toast.success("Guardian created");
      }
      setFormOpen(false);
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setDeleting(true);
    try {
      await deleteGuardian(selected.id);
      toast.success("Guardian deleted");
      setDeleteOpen(false);
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  const columns: Column<Guardian>[] = [
    { key: "full_name", header: "Name", sortable: true },
    { key: "relationship", header: "Relationship", sortable: true, render: (row) => (
      <span className="capitalize text-gray-600">{row.relationship}</span>
    )},
    { key: "phone", header: "Phone", render: (row) => row.phone ? (
      <span className="flex items-center gap-1 text-gray-600"><Phone size={12} />{row.phone}</span>
    ) : <span className="text-gray-400">—</span> },
    { key: "email", header: "Email", render: (row) => row.email ? (
      <span className="flex items-center gap-1 text-gray-600 text-xs"><Mail size={12} />{row.email}</span>
    ) : <span className="text-gray-400">—</span> },
    { key: "student_count", header: "Students", sortable: true, render: (row) => (
      <span className="px-2 py-0.5 bg-violet-50 text-violet-700 rounded-full text-xs font-medium">{row.student_count ?? 0}</span>
    )},
    { key: "is_emergency_contact", header: "Emergency", render: (row) => row.is_emergency_contact ? (
      <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded-full text-xs">Yes</span>
    ) : null },
    {
      key: "id", header: "", render: (row) => (
        <div className="flex gap-1">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row); }}
            className="px-2 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50">Edit</button>
          <button onClick={(e) => { e.stopPropagation(); openDelete(row); }}
            className="px-2 py-1 text-xs border border-red-200 text-red-600 rounded hover:bg-red-50">Delete</button>
        </div>
      )
    },
  ];

  const field = (label: string, key: keyof Guardian, type = "text", required = false) => (
    <FormField label={label} required={required}>
      <input
        type={type}
        value={(form[key] as string) || ""}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
      />
    </FormField>
  );

  return (
    <div className="p-6">
      <PageHeader
        title="Guardians & Parents"
        subtitle="Manage parent and guardian contacts"
        actions={
          <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition-colors">
            <UserPlus size={15} /> Add Guardian
          </button>
        }
      />

      <div className="mb-5">
        <SearchInput value={search} onChange={setSearch} placeholder="Search by name, phone, email…" className="w-72" />
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <DataTable<Guardian>
          columns={columns}
          rows={guardians}
          loading={loading}
          onRowClick={openEdit}
        />
      </div>

      <Modal open={formOpen} onClose={() => setFormOpen(false)}
        title={selected ? "Edit Guardian" : "Add Guardian"} size="lg"
        footer={
          <>
            <button onClick={() => setFormOpen(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {saving ? "Saving…" : "Save"}
            </button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          {field("Full Name", "full_name", "text", true)}
          <FormField label="Relationship" required>
            <select value={form.relationship || "guardian"}
              onChange={(e) => setForm((f) => ({ ...f, relationship: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
            >
              {["father","mother","guardian","grandparent","sibling","other"].map((r) => (
                <option key={r} value={r} className="capitalize">{r}</option>
              ))}
            </select>
          </FormField>
          {field("Phone", "phone")}
          {field("Alt. Phone", "alt_phone")}
          {field("Email", "email", "email")}
          {field("ID Number", "id_number")}
          {field("Occupation", "occupation")}
          <FormField label="Communication Preference">
            <select value={form.communication_pref || "phone"}
              onChange={(e) => setForm((f) => ({ ...f, communication_pref: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30"
            >
              {["phone","email","sms","all"].map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </FormField>
          <div className="col-span-2 flex gap-4">
            {(["is_emergency_contact","is_pickup_authorized","is_billing_contact"] as const).map((k) => (
              <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" checked={!!(form[k])}
                  onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.checked ? 1 : 0 }))}
                  className="w-4 h-4 rounded text-violet-600"
                />
                {k.replace(/is_/,"").replace(/_/g," ")}
              </label>
            ))}
          </div>
          <div className="col-span-2">
            <FormField label="Address">
              <textarea value={form.address || ""} rows={2}
                onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/30 resize-none w-full"
              />
            </FormField>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={handleDelete}
        loading={deleting}
        title="Delete Guardian"
        message={`Delete guardian "${selected?.full_name}"? This cannot be undone.`}
        confirmLabel="Delete"
        danger
      />
    </div>
  );
}
