/**
 * DataTable — shared, typed table component used by every module page.
 *
 * Features:
 *   - Generic typed rows
 *   - Server-side pagination
 *   - Column sorting (visual indicator)
 *   - Skeleton loading rows
 *   - Empty state
 *   - Optional row click handler
 *   - Sticky header
 */

import { useState } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";
import type { LucideIcon } from "lucide-react";

export interface Column<T> {
  key:       keyof T | string;
  header:    string;
  sortable?: boolean;
  width?:    string;
  className?: string;
  render?:   (row: T) => React.ReactNode;
}

export interface PaginationState {
  page:    number;
  perPage: number;
  total:   number;
}

interface DataTableProps<T extends object> {
  columns:       Column<T>[];
  rows:          T[];
  loading?:      boolean;
  keyField?:     keyof T;
  emptyIcon?:    LucideIcon;
  emptyTitle?:   string;
  emptyDesc?:    string;
  pagination?:   PaginationState;
  onPageChange?: (page: number) => void;
  onSort?:       (key: string, dir: "asc" | "desc") => void;
  onRowClick?:   (row: T) => void;
  rowClassName?: (row: T) => string;
  stickyHeader?: boolean;
}

function SortIcon({ dir }: { dir: "asc" | "desc" | null }) {
  if (!dir) return <ChevronsUpDown size={13} className="text-gray-400 ml-1 flex-shrink-0" />;
  return dir === "asc"
    ? <ChevronUp size={13} className="text-violet-600 ml-1 flex-shrink-0" />
    : <ChevronDown size={13} className="text-violet-600 ml-1 flex-shrink-0" />;
}

export function DataTable<T extends object>({
  columns,
  rows,
  loading = false,
  keyField,
  emptyIcon,
  emptyTitle = "No records found",
  emptyDesc,
  pagination,
  onPageChange,
  onSort,
  onRowClick,
  rowClassName,
  stickyHeader = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const handleSort = (col: Column<T>) => {
    if (!col.sortable || !onSort) return;
    const key = col.key as string;
    const newDir = sortKey === key && sortDir === "asc" ? "desc" : "asc";
    setSortKey(key);
    setSortDir(newDir);
    onSort(key, newDir);
  };

  const colCount = columns.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className={stickyHeader ? "overflow-auto max-h-[70vh]" : "overflow-x-auto"}>
        <table className="w-full text-sm">
          <thead className={stickyHeader ? "sticky top-0 z-10" : ""}>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide border-b border-gray-200">
              {columns.map((col) => (
                <th
                  key={col.key as string}
                  className={[
                    "px-4 py-3 select-none",
                    col.width || "",
                    col.sortable && onSort ? "cursor-pointer hover:text-gray-800 transition-colors" : "",
                    col.className || "",
                  ].join(" ")}
                  onClick={() => handleSort(col)}
                >
                  <div className="flex items-center">
                    {col.header}
                    {col.sortable && onSort && (
                      <SortIcon dir={sortKey === col.key ? sortDir : null} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <SkeletonRow key={i} cols={colCount} />
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={colCount} className="py-16">
                  <EmptyState icon={emptyIcon} title={emptyTitle} description={emptyDesc} />
                </td>
              </tr>
            ) : (
              rows.map((row, i) => {
                const key = keyField ? String(row[keyField]) : i;
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={[
                      "hover:bg-gray-50 transition-colors",
                      onRowClick ? "cursor-pointer" : "",
                      rowClassName ? rowClassName(row) : "",
                    ].join(" ")}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key as string}
                        className={["px-4 py-3 text-gray-700", col.className || ""].join(" ")}
                      >
                        {col.render
                          ? col.render(row)
                          : String((row as any)[col.key] ?? "—")}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && pagination.total > pagination.perPage && onPageChange && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
          <span className="text-xs text-gray-500">
            Showing {Math.min((pagination.page - 1) * pagination.perPage + 1, pagination.total)}–
            {Math.min(pagination.page * pagination.perPage, pagination.total)} of {pagination.total}
          </span>
          <div className="flex items-center gap-1">
            <PaginationButton
              label="←"
              disabled={pagination.page <= 1}
              onClick={() => onPageChange(pagination.page - 1)}
            />
            {Array.from({ length: Math.min(5, Math.ceil(pagination.total / pagination.perPage)) }, (_, i) => {
              const totalPages = Math.ceil(pagination.total / pagination.perPage);
              let page: number;
              if (totalPages <= 5) {
                page = i + 1;
              } else if (pagination.page <= 3) {
                page = i + 1;
              } else if (pagination.page >= totalPages - 2) {
                page = totalPages - 4 + i;
              } else {
                page = pagination.page - 2 + i;
              }
              return (
                <PaginationButton
                  key={page}
                  label={String(page)}
                  active={page === pagination.page}
                  onClick={() => onPageChange(page)}
                />
              );
            })}
            <PaginationButton
              label="→"
              disabled={pagination.page >= Math.ceil(pagination.total / pagination.perPage)}
              onClick={() => onPageChange(pagination.page + 1)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function PaginationButton({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={[
        "w-7 h-7 flex items-center justify-center rounded text-xs font-medium transition-colors",
        active
          ? "bg-violet-600 text-white"
          : disabled
          ? "text-gray-300 cursor-not-allowed"
          : "text-gray-600 hover:bg-gray-200",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

export default DataTable;
