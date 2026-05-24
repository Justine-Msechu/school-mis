import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import type { ResultReport, ResultRow, Subject } from "@/api/grades";
import GradeCell from "./GradeCell";
import GradeBadge from "@/components/ui/GradeBadge";
import SkeletonRow from "@/components/ui/SkeletonRow";
import EmptyState from "@/components/ui/EmptyState";
import { BookOpen } from "lucide-react";

const PAGE_SIZE = 30;

function SortIcon({ sorted }: { sorted: false | "asc" | "desc" }) {
  if (sorted === "asc")  return <ChevronUp size={12} className="inline ml-1" />;
  if (sorted === "desc") return <ChevronDown size={12} className="inline ml-1" />;
  return <ChevronsUpDown size={11} className="inline ml-1 opacity-30" />;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildColumns(subjects: Subject[], isSecondary: boolean): ColumnDef<ResultRow, any>[] {
  const helper = createColumnHelper<ResultRow>();

  return [
    // ── Frozen identity ───────────────────────────────────────────────────────
    helper.accessor("rank", {
      id: "rank",
      header: "#",
      size: 44,
      meta: { frozen: "left", groupStart: true, groupEnd: false },
      cell: (i) => (
        <span className="font-semibold text-gray-500 text-xs">{i.getValue() as string | number}</span>
      ),
    }),
    helper.accessor("student_name", {
      id: "student_name",
      header: "Student",
      size: 190,
      meta: { frozen: "left", groupStart: false, groupEnd: false },
      cell: (i) => <span className="font-medium text-gray-900 truncate block">{i.getValue() as string}</span>,
    }),
    helper.accessor("admission_no", {
      id: "admission_no",
      header: "Adm No",
      size: 80,
      meta: { frozen: "left", groupStart: false, groupEnd: true },
      cell: (i) => <span className="text-gray-500 text-xs">{i.getValue() as string}</span>,
    }),

    // ── Scrollable subject columns ────────────────────────────────────────────
    ...subjects.map((s, idx) =>
      helper.accessor((row) => row.grades[s.id], {
        id: `subj_${s.id}`,
        header: s.code || s.name.slice(0, 3).toUpperCase(),
        size: 68,
        enableSorting: false,
        meta: {
          frozen: false,
          fullHeader: s.name,
          groupStart: idx === 0,
          groupEnd: idx === subjects.length - 1,
        },
        cell: (i) => {
          const g = i.getValue() as { score: number; grade_letter: string } | undefined;
          return <GradeCell score={g?.score ?? null} letter={g?.grade_letter ?? null} />;
        },
      })
    ),

    // ── Frozen summary ────────────────────────────────────────────────────────
    helper.accessor("total", {
      id: "total",
      header: "Total",
      size: 80,
      meta: { frozen: "right", groupStart: true, groupEnd: false },
      cell: (i) => {
        const row = i.row.original;
        return (
          <span className="text-xs text-gray-700">
            {row.max_total ? `${row.total}/${row.max_total}` : "—"}
          </span>
        );
      },
    }),
    helper.accessor("average", {
      id: "average",
      header: "Avg %",
      size: 64,
      meta: { frozen: "right", groupStart: false, groupEnd: false },
      cell: (i) => {
        const v = i.getValue() as number | null;
        return <span className="text-xs font-medium text-gray-700">{v !== null ? `${v.toFixed(1)}%` : "—"}</span>;
      },
    }),
    helper.accessor("overall_grade", {
      id: "overall_grade",
      header: "Grade",
      size: 56,
      meta: { frozen: "right", groupStart: false, groupEnd: isSecondary ? false : true },
      cell: (i) => <GradeBadge letter={i.getValue() as string} />,
    }),
    ...(isSecondary
      ? [
          helper.accessor("gpa", {
            id: "gpa",
            header: "GPA",
            size: 56,
            meta: { frozen: "right", groupStart: false, groupEnd: true },
            cell: (i) => {
              const v = i.getValue() as number | null;
              return v !== null ? (
                <span className="text-xs font-bold text-violet-600">{v.toFixed(2)}</span>
              ) : <span className="text-gray-300">—</span>;
            },
          }) as ColumnDef<ResultRow, unknown>,
        ]
      : []),
  ];
}

function thClass(frozen: string | boolean | undefined, groupStart: boolean | undefined, groupEnd: boolean | undefined) {
  return clsx(
    "px-3 py-2.5 text-left text-xs font-semibold text-gray-500 bg-gray-50 whitespace-nowrap select-none",
    "border-b border-gray-200",
    frozen === "left"  && "col-frozen-left  bg-gray-50 shadow-[2px_0_4px_-1px_rgba(0,0,0,0.08)]",
    frozen === "right" && "col-frozen-right bg-gray-50 shadow-[-2px_0_4px_-1px_rgba(0,0,0,0.08)]",
    groupStart && frozen === false && "border-l-2 border-l-gray-200",
    groupEnd   && frozen !== false && "border-r-2 border-r-gray-200",
  );
}

function tdClass(frozen: string | boolean | undefined, groupStart: boolean | undefined) {
  return clsx(
    "px-3 py-2 text-sm border-b border-gray-100",
    frozen === "left"  && "col-frozen-left  bg-white shadow-[2px_0_4px_-1px_rgba(0,0,0,0.05)]",
    frozen === "right" && "col-frozen-right bg-white shadow-[-2px_0_4px_-1px_rgba(0,0,0,0.05)]",
    groupStart && frozen === false && "border-l-2 border-l-gray-100",
  );
}

interface ResultsTableProps {
  report: ResultReport;
  loading?: boolean;
  search: string;
}

export default function ResultsTable({ report, loading, search }: ResultsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "rank", desc: false }]);

  const filtered = useMemo(() => {
    if (!search.trim()) return report.rows;
    const q = search.toLowerCase();
    return report.rows.filter(
      (r) => r.student_name.toLowerCase().includes(q) || r.admission_no.toLowerCase().includes(q)
    );
  }, [report.rows, search]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns = useMemo<ColumnDef<ResultRow, any>[]>(
    () => buildColumns(report.subjects, report.school_type === "secondary"),
    [report.subjects, report.school_type]
  );

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: PAGE_SIZE } },
  });

  const { pageIndex, pageSize } = table.getState().pagination;
  const totalRows = filtered.length;
  const start = pageIndex * pageSize + 1;
  const end = Math.min((pageIndex + 1) * pageSize, totalRows);

  if (!loading && report.rows.length === 0) {
    return <EmptyState icon={BookOpen} title="No results" description="No grade data for this exam and class yet." />;
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Table wrapper with horizontal scroll on subjects only */}
      <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm" style={{ minWidth: 600 }}>
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => {
                    const meta = (header.column.columnDef.meta ?? {}) as Record<string, unknown>;
                    const sorted = header.column.getIsSorted();
                    const canSort = header.column.getCanSort();
                    return (
                      <th
                        key={header.id}
                        style={{ width: header.getSize() }}
                        className={thClass(meta.frozen as string | undefined, meta.groupStart as boolean, meta.groupEnd as boolean)}
                        title={meta.fullHeader as string | undefined}
                        onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                      >
                        <span className={clsx("inline-flex items-center", canSort && "cursor-pointer hover:text-gray-800")}>
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {canSort && <SortIcon sorted={sorted} />}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={columns.length} />)
                : table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                      {row.getVisibleCells().map((cell) => {
                        const meta = (cell.column.columnDef.meta ?? {}) as Record<string, unknown>;
                        return (
                          <td key={cell.id} className={tdClass(meta.frozen as string | undefined, meta.groupStart as boolean)}>
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalRows > PAGE_SIZE && (
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Showing {start}–{end} of {totalRows} students</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="flex items-center justify-center w-7 h-7 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-100"
            >
              <ChevronLeft size={13} />
            </button>
            {table.getPageOptions().slice(
              Math.max(0, pageIndex - 2),
              Math.min(table.getPageCount(), pageIndex + 3)
            ).map((p) => (
              <button
                key={p}
                onClick={() => table.setPageIndex(p)}
                className={clsx(
                  "flex items-center justify-center w-7 h-7 border rounded-lg text-xs font-medium",
                  p === pageIndex
                    ? "bg-violet-600 text-white border-violet-600"
                    : "border-gray-200 hover:bg-gray-100"
                )}
              >
                {p + 1}
              </button>
            ))}
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="flex items-center justify-center w-7 h-7 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-100"
            >
              <ChevronRight size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
