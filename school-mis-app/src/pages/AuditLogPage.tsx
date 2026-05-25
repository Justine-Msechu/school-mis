import { useState, useEffect, useRef } from "react";
import { Shield, Search } from "lucide-react";
import { getAuditLog } from "@/api/notifications";
import DataTable from "@/components/data/DataTable";
import Select from "@/components/ui/Select";
import type { Column } from "@/components/data/DataTable";

interface AuditEntry {
  id:         number;
  user_id:    number;
  username:   string;
  full_name:  string;
  role:       string;
  action:     string;
  table_name: string;
  record_id:  number | null;
  detail:     string;
  ts:         string;
}

const ACTION_COLORS: Record<string, string> = {
  INSERT:  "bg-green-100 text-green-700",
  UPDATE:  "bg-blue-100 text-blue-700",
  DELETE:  "bg-red-100 text-red-700",
  APPROVE: "bg-violet-100 text-violet-700",
  PUBLISH: "bg-cyan-100 text-cyan-700",
  RETURN:  "bg-amber-100 text-amber-700",
  REVERSE: "bg-orange-100 text-orange-700",
  LOGIN:   "bg-gray-100 text-gray-700",
  LOGOUT:  "bg-gray-100 text-gray-600",
  SUBMIT:  "bg-indigo-100 text-indigo-700",
  RESOLVE: "bg-teal-100 text-teal-700",
};

const TABLE_OPTIONS = [
  { value: null as null, label: "All Tables" },
  { value: "grades",       label: "Grades" },
  { value: "fee_payments", label: "Payments" },
  { value: "expenses",     label: "Expenses" },
  { value: "students",     label: "Students" },
  { value: "teachers",     label: "Teachers" },
  { value: "grade_change_requests", label: "Change Requests" },
];

const ACTION_OPTIONS = [
  { value: null as null, label: "All Actions" },
  { value: "INSERT",  label: "Insert" },
  { value: "UPDATE",  label: "Update" },
  { value: "DELETE",  label: "Delete" },
  { value: "APPROVE", label: "Approve" },
  { value: "PUBLISH", label: "Publish" },
  { value: "RETURN",  label: "Return" },
  { value: "REVERSE", label: "Reverse" },
  { value: "SUBMIT",  label: "Submit" },
  { value: "LOGIN",   label: "Login" },
];

const COLUMNS: Column<AuditEntry>[] = [
  {
    key: "ts",
    header: "Timestamp",
    render: (r) => (
      <span className="text-xs text-gray-500 font-mono">
        {new Date(r.ts).toLocaleString()}
      </span>
    ),
  },
  {
    key: "full_name",
    header: "Actor",
    render: (r) => (
      <div>
        <div className="font-medium text-gray-900 text-sm">{r.full_name || r.username || "—"}</div>
        <div className="text-xs text-gray-400 capitalize">{r.role}</div>
      </div>
    ),
  },
  {
    key: "action",
    header: "Action",
    render: (r) => (
      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${ACTION_COLORS[r.action] || "bg-gray-100 text-gray-700"}`}>
        {r.action}
      </span>
    ),
  },
  {
    key: "table_name",
    header: "Table",
    render: (r) => (
      <span className="font-mono text-xs text-gray-600">{r.table_name}</span>
    ),
  },
  {
    key: "record_id",
    header: "Record",
    render: (r) => (
      <span className="text-xs text-gray-500">#{r.record_id || "—"}</span>
    ),
  },
  {
    key: "detail",
    header: "Detail",
    render: (r) => (
      <span className="text-xs text-gray-500 truncate max-w-xs block" title={r.detail}>
        {r.detail || "—"}
      </span>
    ),
  },
];

export default function AuditLogPage() {
  const [rows,      setRows]      = useState<AuditEntry[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [table,     setTable]     = useState<string | null>(null);
  const [action,    setAction]    = useState<string | null>(null);
  const firstLoad = useRef(true);

  const load = () => {
    if (firstLoad.current) setLoading(true);
    getAuditLog({ table_name: table ?? undefined, action: action ?? undefined, limit: 200 })
      .then((d) => { setRows(d as AuditEntry[]); firstLoad.current = false; })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [table, action]);

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-sm text-gray-500 mt-0.5">Complete trail of all system activity</p>
      </div>

      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <Select
          value={table}
          onChange={(v) => { setTable(v as string | null); firstLoad.current = true; }}
          options={TABLE_OPTIONS}
          className="w-44"
        />
        <Select
          value={action}
          onChange={(v) => { setAction(v as string | null); firstLoad.current = true; }}
          options={ACTION_OPTIONS}
          className="w-40"
        />
        <span className="text-sm text-gray-400">{rows.length} entries</span>
      </div>

      <DataTable
        columns={COLUMNS}
        rows={rows}
        loading={loading}
        keyField="id"
        emptyIcon={Shield}
        emptyTitle="No audit entries"
        emptyDesc="System activity will appear here."
      />
    </div>
  );
}
