import { useEffect, useState, useCallback } from "react";
import {
  AlertTriangle, RefreshCw, CheckCircle2, Trash2,
  ChevronDown, ChevronUp, Monitor, Globe,
} from "lucide-react";
import {
  getErrorLogs, resolveError, clearResolvedErrors, getErrorDetail,
  type ErrorLogItem,
} from "@/api/errorLogs";

const fmtDate = (s: string) =>
  new Date(s).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "medium" });

function SourceBadge({ source }: { source: string }) {
  return source === "backend"
    ? <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"><Monitor size={10}/>Backend</span>
    : <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"><Globe size={10}/>Frontend</span>;
}

function ErrorRow({ item, onResolve }: { item: ErrorLogItem; onResolve: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail]     = useState<any>(null);
  const [resolving, setResolving] = useState(false);

  const load = async () => {
    if (!detail) {
      const { getErrorDetail: gd } = await import("@/api/errorLogs");
      setDetail(await gd(item.id));
    }
    setExpanded(v => !v);
  };

  const handleResolve = async () => {
    setResolving(true);
    await resolveError(item.id).catch(() => {});
    onResolve();
  };

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer"
        onClick={load}
      >
        <td className="px-3 py-2.5 text-xs text-gray-500 whitespace-nowrap">{fmtDate(item.ts)}</td>
        <td className="px-3 py-2.5"><SourceBadge source={item.source} /></td>
        <td className="px-3 py-2.5 text-xs font-mono text-gray-600 max-w-[120px] truncate">{item.path || "—"}</td>
        <td className="px-3 py-2.5 text-xs text-gray-500">{item.role || "—"}</td>
        <td className="px-3 py-2.5 text-sm text-gray-800 max-w-xs truncate">{item.message}</td>
        <td className="px-3 py-2.5 text-right">
          <div className="flex items-center justify-end gap-2">
            {!item.resolved && (
              <button
                onClick={(e) => { e.stopPropagation(); handleResolve(); }}
                disabled={resolving}
                className="p-1 rounded hover:bg-green-100 text-green-600 disabled:opacity-40"
                title="Mark resolved"
              >
                <CheckCircle2 size={14} />
              </button>
            )}
            {expanded ? <ChevronUp size={14} className="text-gray-400"/> : <ChevronDown size={14} className="text-gray-400"/>}
          </div>
        </td>
      </tr>
      {expanded && detail && (
        <tr className="bg-gray-50">
          <td colSpan={6} className="px-4 py-3">
            <div className="space-y-2">
              {detail.error_type && (
                <p className="text-xs"><span className="font-medium text-gray-600">Type:</span> <span className="font-mono">{detail.error_type}</span></p>
              )}
              {detail.request_id && (
                <p className="text-xs"><span className="font-medium text-gray-600">Request ID:</span> <span className="font-mono text-violet-700">{detail.request_id}</span></p>
              )}
              {detail.stack && (
                <pre className="text-xs font-mono bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto max-h-48 whitespace-pre-wrap">
                  {detail.stack}
                </pre>
              )}
              {detail.context && detail.context !== "{}" && (
                <pre className="text-xs font-mono bg-gray-100 p-3 rounded-lg overflow-x-auto max-h-32 whitespace-pre-wrap">
                  {typeof detail.context === "string" ? detail.context : JSON.stringify(detail.context, null, 2)}
                </pre>
              )}
              {detail.resolved_at && (
                <p className="text-xs text-green-700">Resolved at {fmtDate(detail.resolved_at)}</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ErrorLogsPage() {
  const [items,     setItems]     = useState<ErrorLogItem[]>([]);
  const [total,     setTotal]     = useState(0);
  const [loading,   setLoading]   = useState(true);
  const [source,    setSource]    = useState<string>("");
  const [resolved,  setResolved]  = useState(0);
  const [clearing,  setClearing]  = useState(false);
  const [page,      setPage]      = useState(0);
  const PER_PAGE = 50;

  const load = useCallback(() => {
    setLoading(true);
    getErrorLogs({
      source:   source || undefined,
      resolved,
      limit:    PER_PAGE,
      offset:   page * PER_PAGE,
    }).then(d => { setItems(d.items); setTotal(d.total); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [source, resolved, page]);

  useEffect(() => { load(); }, [load]);

  const handleClearResolved = async () => {
    setClearing(true);
    await clearResolvedErrors().catch(() => {});
    setClearing(false);
    load();
  };

  const unresolved = resolved === 0;

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Error Logs</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} {unresolved ? "unresolved" : "resolved"} error{total !== 1 ? "s" : ""}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Source filter */}
          <select
            value={source}
            onChange={e => { setSource(e.target.value); setPage(0); }}
            className="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-400"
          >
            <option value="">All sources</option>
            <option value="backend">Backend</option>
            <option value="frontend">Frontend</option>
          </select>

          {/* Resolved toggle */}
          <button
            onClick={() => { setResolved(v => v === 0 ? 1 : 0); setPage(0); }}
            className={`h-8 px-3 text-xs font-medium rounded-lg border transition-colors ${
              resolved === 1
                ? "bg-green-50 text-green-700 border-green-200"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            {resolved === 1 ? "Showing resolved" : "Show resolved"}
          </button>

          {resolved === 1 && (
            <button
              onClick={handleClearResolved}
              disabled={clearing}
              className="h-8 px-3 text-xs font-medium rounded-lg border border-red-200 text-red-600 hover:bg-red-50 flex items-center gap-1 disabled:opacity-50"
            >
              <Trash2 size={12}/> Clear resolved
            </button>
          )}

          <button
            onClick={load}
            disabled={loading}
            className="h-8 w-8 flex items-center justify-center rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <RefreshCw size={20} className="animate-spin text-violet-500" />
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
            <CheckCircle2 size={28} className="opacity-40" />
            <p className="text-sm">{unresolved ? "No unresolved errors — all clear!" : "No resolved errors."}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-3 py-2 text-left">Time</th>
                  <th className="px-3 py-2 text-left">Source</th>
                  <th className="px-3 py-2 text-left">Path</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-left">Message</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map(item => (
                  <ErrorRow key={item.id} item={item} onResolve={load} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > PER_PAGE && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Showing {page * PER_PAGE + 1}–{Math.min((page + 1) * PER_PAGE, total)} of {total}</span>
          <div className="flex gap-2">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50">Prev</button>
            <button disabled={(page + 1) * PER_PAGE >= total} onClick={() => setPage(p => p + 1)} className="px-3 py-1 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
