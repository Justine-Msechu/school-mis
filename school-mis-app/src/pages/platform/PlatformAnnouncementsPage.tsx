import { useEffect, useState } from "react";
import { Megaphone, Plus, Trash2, RefreshCw, AlertTriangle, Info, AlertCircle, X } from "lucide-react";
import {
  listAnnouncements, createAnnouncement, deleteAnnouncement,
  type Announcement, type AnnouncementPayload,
} from "@/api/schools";

const PLANS = ["all", "trial", "basic", "standard", "premium"] as const;
const PRIORITIES = ["normal", "warning", "critical"] as const;

const PRIORITY_META = {
  normal:   { label: "Normal",   color: "#2563EB", bg: "#EFF6FF", icon: Info },
  warning:  { label: "Warning",  color: "#D97706", bg: "#FFFBEB", icon: AlertTriangle },
  critical: { label: "Critical", color: "#DC2626", bg: "#FEF2F2", icon: AlertCircle },
} as const;

const EMPTY: AnnouncementPayload = {
  title: "", body: "", priority: "normal", target_plan: "all", expires_at: null,
};

export default function PlatformAnnouncementsPage() {
  const [items,   setItems]   = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");
  const [form,    setForm]    = useState<AnnouncementPayload>(EMPTY);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await listAnnouncements();
      setItems(res.data);
    } catch {
      setError("Failed to load announcements.");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.title.trim() || !form.body.trim()) {
      setCreateError("Title and body are required.");
      return;
    }
    setCreating(true); setCreateError("");
    try {
      await createAnnouncement({ ...form, expires_at: form.expires_at || null });
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch {
      setCreateError("Failed to create announcement.");
    } finally { setCreating(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this announcement?")) return;
    setDeleting(id);
    try {
      await deleteAnnouncement(id);
      setItems(i => i.filter(a => a.id !== id));
    } finally { setDeleting(null); }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Announcements</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Broadcast notices to school admins on their dashboards
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => setShowForm(f => !f)}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
          >
            <Plus size={15} />
            New Announcement
          </button>
        </div>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-2xl border border-violet-200 shadow-sm p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">Create Announcement</h2>
            <button onClick={() => setShowForm(false)} className="p-1 rounded hover:bg-gray-100 text-gray-400">
              <X size={16} />
            </button>
          </div>

          {createError && (
            <div className="mb-3 px-3 py-2.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
              {createError}
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Scheduled maintenance on 2026-06-01"
                className="w-full h-9 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Message</label>
              <textarea
                value={form.body}
                onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
                rows={3}
                placeholder="Announcement details visible to school admins…"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 resize-none"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                <select
                  value={form.priority}
                  onChange={e => setForm(f => ({ ...f, priority: e.target.value as typeof form.priority }))}
                  className="w-full h-9 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {PRIORITIES.map(p => (
                    <option key={p} value={p}>{PRIORITY_META[p].label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Target plan</label>
                <select
                  value={form.target_plan}
                  onChange={e => setForm(f => ({ ...f, target_plan: e.target.value }))}
                  className="w-full h-9 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                >
                  {PLANS.map(p => (
                    <option key={p} value={p} className="capitalize">{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Expires (optional)</label>
                <input
                  type="date"
                  value={form.expires_at ?? ""}
                  onChange={e => setForm(f => ({ ...f, expires_at: e.target.value || null }))}
                  className="w-full h-9 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              onClick={() => { setShowForm(false); setForm(EMPTY); setCreateError(""); }}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="px-4 py-2 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-60 rounded-lg transition-colors"
            >
              {creating ? "Publishing…" : "Publish"}
            </button>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-7 h-7 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 text-sm text-red-700">{error}</div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <Megaphone size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 text-sm">No announcements yet.</p>
          <p className="text-gray-400 text-xs mt-1">Click "New Announcement" to broadcast a message to all schools.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(ann => {
            const meta = PRIORITY_META[ann.priority] ?? PRIORITY_META.normal;
            const MetaIcon = meta.icon;
            const isExpired = ann.expires_at && ann.expires_at < new Date().toISOString().slice(0, 10);
            return (
              <div
                key={ann.id}
                className={`bg-white rounded-2xl border shadow-sm p-5 ${isExpired ? "opacity-50" : ""}`}
                style={{ borderColor: `${meta.color}30` }}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ backgroundColor: meta.bg }}>
                    <MetaIcon size={15} style={{ color: meta.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{ann.title}</p>
                        <p className="text-xs text-gray-600 mt-1 leading-relaxed">{ann.body}</p>
                      </div>
                      <button
                        onClick={() => handleDelete(ann.id)}
                        disabled={deleting === ann.id}
                        className="flex-shrink-0 p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors disabled:opacity-40"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div className="flex items-center gap-3 mt-2.5 flex-wrap">
                      <span
                        className="text-xs font-semibold px-2 py-0.5 rounded-full capitalize"
                        style={{ backgroundColor: meta.bg, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="text-xs text-gray-400 capitalize">
                        Plan: <span className="font-medium text-gray-600">{ann.target_plan}</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        Published: <span className="font-medium text-gray-600">{ann.created_at.slice(0, 10)}</span>
                      </span>
                      {ann.expires_at && (
                        <span className={`text-xs ${isExpired ? "text-red-400" : "text-gray-400"}`}>
                          {isExpired ? "Expired" : "Expires"}: <span className="font-medium">{ann.expires_at}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
