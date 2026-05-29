import { useEffect, useState, useRef, useCallback } from "react";
import {
  Upload, Trash2, Eye, EyeOff, ChevronUp, ChevronDown,
  Image, ImagePlus, RefreshCw, X,
} from "lucide-react";
import {
  getMedia, uploadMedia, updateMedia, deleteMedia, mediaUrl,
  type LandingMediaItem, type MediaType,
} from "@/api/landingMedia";

const TYPE_LABEL: Record<MediaType, string> = {
  poster:     "Offer Poster",
  banner:     "Hero Banner",
  screenshot: "Screenshot",
};

const TYPE_COLOR: Record<MediaType, string> = {
  poster:     "bg-violet-100 text-violet-700",
  banner:     "bg-blue-100 text-blue-700",
  screenshot: "bg-emerald-100 text-emerald-700",
};

function MediaCard({
  item,
  onUpdate,
  onDelete,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast,
}: {
  item:       LandingMediaItem;
  onUpdate:   (id: number, patch: Parameters<typeof updateMedia>[1]) => Promise<void>;
  onDelete:   (id: number) => Promise<void>;
  onMoveUp:   (id: number) => void;
  onMoveDown: (id: number) => void;
  isFirst:    boolean;
  isLast:     boolean;
}) {
  const [editing,  setEditing]  = useState(false);
  const [title,    setTitle]    = useState(item.title ?? "");
  const [desc,     setDesc]     = useState(item.description ?? "");
  const [type,     setType]     = useState<MediaType>(item.media_type);
  const [saving,   setSaving]   = useState(false);
  const [deleting, setDeleting] = useState(false);

  const save = async () => {
    setSaving(true);
    await onUpdate(item.id, { title, description: desc, media_type: type });
    setSaving(false);
    setEditing(false);
  };

  const remove = async () => {
    if (!confirm(`Delete "${item.title || item.filename}"?`)) return;
    setDeleting(true);
    await onDelete(item.id);
  };

  const toggleVisible = () => onUpdate(item.id, { is_active: item.is_active ? 0 : 1 });

  return (
    <div className={`bg-white rounded-2xl border ${item.is_active ? "border-gray-100" : "border-gray-200 opacity-60"} shadow-sm overflow-hidden`}>
      {/* Image */}
      <div className="relative aspect-video bg-gray-100 overflow-hidden">
        <img
          src={mediaUrl(item.filename)}
          alt={item.title ?? "media"}
          className="w-full h-full object-cover"
        />
        <div className="absolute top-2 left-2">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TYPE_COLOR[item.media_type]}`}>
            {TYPE_LABEL[item.media_type]}
          </span>
        </div>
        {!item.is_active && (
          <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
            <span className="text-xs font-semibold text-gray-500 bg-white px-2 py-1 rounded-lg border">Hidden</span>
          </div>
        )}
      </div>

      {/* Info / edit */}
      <div className="p-3">
        {editing ? (
          <div className="space-y-2">
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Title (optional)"
              className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-400"
            />
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="Description (optional)"
              rows={2}
              className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-400 resize-none"
            />
            <select
              value={type}
              onChange={e => setType(e.target.value as MediaType)}
              className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-400"
            >
              <option value="poster">Offer Poster</option>
              <option value="banner">Hero Banner</option>
              <option value="screenshot">Screenshot</option>
            </select>
            <div className="flex gap-2 pt-1">
              <button onClick={save} disabled={saving}
                className="flex-1 py-1.5 text-xs font-semibold text-white bg-violet-600 rounded-lg hover:bg-violet-700 disabled:opacity-50">
                {saving ? "Saving…" : "Save"}
              </button>
              <button onClick={() => setEditing(false)}
                className="flex-1 py-1.5 text-xs font-semibold text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-sm font-semibold text-gray-800 truncate">{item.title || <span className="text-gray-400 font-normal italic">No title</span>}</p>
            {item.description && <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{item.description}</p>}
            <div className="flex items-center justify-between mt-3 gap-1">
              {/* Order controls */}
              <div className="flex gap-0.5">
                <button onClick={() => onMoveUp(item.id)} disabled={isFirst}
                  className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 disabled:opacity-30">
                  <ChevronUp size={14} />
                </button>
                <button onClick={() => onMoveDown(item.id)} disabled={isLast}
                  className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 disabled:opacity-30">
                  <ChevronDown size={14} />
                </button>
              </div>
              <div className="flex gap-1">
                <button onClick={toggleVisible}
                  className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100"
                  title={item.is_active ? "Hide from landing page" : "Show on landing page"}>
                  {item.is_active ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
                <button onClick={() => setEditing(true)}
                  className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100">
                  <Image size={14} />
                </button>
                <button onClick={remove} disabled={deleting}
                  className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 disabled:opacity-40">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function PlatformMediaPage() {
  const [items,        setItems]        = useState<LandingMediaItem[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [uploading,    setUploading]    = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview,      setPreview]      = useState<{ url: string; name: string } | null>(null);
  const [form,         setForm]         = useState({ title: "", description: "", media_type: "poster" as MediaType });
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await getMedia(false)); } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleFilePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setSelectedFile(f);
    setPreview({ url: URL.createObjectURL(f), name: f.name });
  };

  const clearFile = () => {
    setSelectedFile(null);
    setPreview(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", selectedFile);
      fd.append("title", form.title);
      fd.append("description", form.description);
      fd.append("media_type", form.media_type);
      await uploadMedia(fd);
      clearFile();
      setForm({ title: "", description: "", media_type: "poster" });
      await load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(msg ?? "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleUpdate = async (id: number, patch: Parameters<typeof updateMedia>[1]) => {
    await updateMedia(id, patch);
    await load();
  };

  const handleDelete = async (id: number) => {
    await deleteMedia(id);
    await load();
  };

  const moveItem = async (id: number, direction: "up" | "down") => {
    const idx = items.findIndex(i => i.id === id);
    if (idx === -1) return;
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= items.length) return;
    const a = items[idx], b = items[swapIdx];
    await Promise.all([
      updateMedia(a.id, { sort_order: b.sort_order }),
      updateMedia(b.id, { sort_order: a.sort_order }),
    ]);
    await load();
  };

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Landing Page Media</h1>
          <p className="text-sm text-gray-500 mt-0.5">Upload images, offer posters, and banners shown on the public landing page.</p>
        </div>
        <button onClick={load} disabled={loading}
          className="h-8 w-8 flex items-center justify-center rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Upload card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <p className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <ImagePlus size={15} className="text-violet-500" /> Upload new image
        </p>

        {/* File input always mounted so the ref stays valid after preview is shown */}
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={handleFilePick}
          className="hidden"
        />

        {!preview ? (
          <label
            onClick={() => fileRef.current?.click()}
            className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-xl p-8 cursor-pointer hover:border-violet-400 hover:bg-violet-50 transition-colors"
          >
            <Upload size={28} className="text-gray-300 mb-2" />
            <span className="text-sm text-gray-500">Click to choose a file</span>
            <span className="text-xs text-gray-400 mt-1">JPEG, PNG, WebP, GIF — max 5 MB</span>
          </label>
        ) : (
          <div className="space-y-3">
            <div className="relative rounded-xl overflow-hidden bg-gray-100 max-h-48">
              <img src={preview.url} alt={preview.name} className="w-full object-contain max-h-48" />
              <button
                onClick={clearFile}
                className="absolute top-2 right-2 p-1 bg-white rounded-lg shadow text-gray-500 hover:text-red-500"
              >
                <X size={14} />
              </button>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <input
                value={form.title}
                onChange={e => setForm(f => ({...f, title: e.target.value}))}
                placeholder="Title (optional)"
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
              <input
                value={form.description}
                onChange={e => setForm(f => ({...f, description: e.target.value}))}
                placeholder="Short description (optional)"
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
              <select
                value={form.media_type}
                onChange={e => setForm(f => ({...f, media_type: e.target.value as MediaType}))}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              >
                <option value="poster">Offer Poster</option>
                <option value="banner">Hero Banner</option>
                <option value="screenshot">Screenshot</option>
              </select>
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-2.5 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-xl disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {uploading ? <><RefreshCw size={14} className="animate-spin" /> Uploading…</> : <><Upload size={14} /> Upload</>}
            </button>
          </div>
        )}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <RefreshCw size={20} className="animate-spin text-violet-400" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
          <Image size={32} className="opacity-30" />
          <p className="text-sm">No media uploaded yet.</p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span>{items.length} item{items.length !== 1 ? "s" : ""}</span>
            <span className="text-gray-300">·</span>
            <span>{items.filter(i => i.is_active).length} visible</span>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {items.map((item, idx) => (
              <MediaCard
                key={item.id}
                item={item}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
                onMoveUp={id => moveItem(id, "up")}
                onMoveDown={id => moveItem(id, "down")}
                isFirst={idx === 0}
                isLast={idx === items.length - 1}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
