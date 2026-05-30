"use client";

import { useMemo, useState } from "react";
import { str, textDir, truncate } from "@/lib/format";
import { rowsToCsv, downloadText } from "@/lib/derive";
import type { JsonRecord } from "@/lib/types";

const PAGE_SIZE = 15;

export function DataTable({
  rows,
  columns,
  onRowClick,
  selectedKey,
  selectedRowId,
  emptyMessage = "No rows to display.",
  pageSize = PAGE_SIZE,
  showPagination = true,
  searchable = true,
  downloadable = true,
  stickyHeader = true,
  showRowActions = false,
  showCopyJsonAction,
}: {
  rows: JsonRecord[];
  columns: { key: string; label: string; render?: (row: JsonRecord) => React.ReactNode; defaultVisible?: boolean }[];
  onRowClick?: (row: JsonRecord) => void;
  selectedKey?: string;
  selectedRowId?: string;
  emptyMessage?: string;
  pageSize?: number;
  showPagination?: boolean;
  searchable?: boolean;
  downloadable?: boolean;
  stickyHeader?: boolean;
  showRowActions?: boolean;
  /** Alias for showRowActions; defaults false to avoid duplicate Actions columns. */
  showCopyJsonAction?: boolean;
}) {
  const copyJsonEnabled = showCopyJsonAction ?? showRowActions;
  const [sortKey, setSortKey] = useState(columns[0]?.key ?? "");
  const [asc, setAsc] = useState(true);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(columns.map((c) => [c.key, c.defaultVisible !== false])),
  );

  const activeColumns = columns.filter((c) => visibleCols[c.key] !== false);

  const filtered = useMemo(() => {
    if (!search.trim()) return rows;
    const q = search.toLowerCase();
    return rows.filter((row) =>
      activeColumns.some((col) => str(row[col.key]).toLowerCase().includes(q)),
    );
  }, [rows, search, activeColumns]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = str(a[sortKey]);
      const bv = str(b[sortKey]);
      if (av === bv) return 0;
      const cmp = av.localeCompare(bv, undefined, { numeric: true });
      return asc ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sortKey, asc]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageRows = showPagination ? sorted.slice(page * pageSize, page * pageSize + pageSize) : sorted;

  if (!rows.length) {
    return <p className="empty-inline">{emptyMessage}</p>;
  }

  const toggleCol = (key: string) => setVisibleCols((v) => ({ ...v, [key]: !v[key] }));

  return (
    <div className="table-wrap" role="region" aria-label="Data table">
      <div className="table-toolbar">
        {searchable ? (
          <input
            type="search"
            className="table-search"
            placeholder="Search table…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            aria-label="Search table"
          />
        ) : null}
        <span className="table-count">{sorted.length} row{sorted.length === 1 ? "" : "s"}</span>
        {downloadable ? (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => downloadText("table_export.csv", rowsToCsv(sorted, activeColumns.map((c) => c.key)))}
          >
            Download CSV
          </button>
        ) : null}
        <details className="col-toggle">
          <summary>Columns</summary>
          <div className="col-toggle-list">
            {columns.map((c) => (
              <label key={c.key}>
                <input type="checkbox" checked={visibleCols[c.key] !== false} onChange={() => toggleCol(c.key)} />
                {c.label}
              </label>
            ))}
          </div>
        </details>
      </div>
      <div className="table-scroll">
        <table className={`data-table ${stickyHeader ? "sticky-head" : ""}`}>
          <thead>
            <tr>
              {activeColumns.map((col) => (
                <th key={col.key}>
                  <button
                    type="button"
                    className="th-sort"
                    onClick={() => {
                      if (sortKey === col.key) setAsc(!asc);
                      else {
                        setSortKey(col.key);
                        setAsc(true);
                      }
                      setPage(0);
                    }}
                    aria-label={`Sort by ${col.label}`}
                  >
                    {col.label}
                  </button>
                </th>
              ))}
              {copyJsonEnabled ? <th aria-label="Row actions">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, idx) => {
              const rowId = `${str(row.case_id)}-${str(row.variant_id)}-${idx}`;
              const selected = selectedRowId === rowId || (selectedKey && str(row[selectedKey]) === selectedRowId);
              return (
                <tr
                  key={rowId}
                  className={`${onRowClick ? "clickable" : ""} ${selected ? "row-selected" : ""}`}
                  onClick={() => onRowClick?.(row)}
                  aria-selected={selected || undefined}
                >
                  {activeColumns.map((col) => {
                    const raw = row[col.key];
                    const content = col.render ? col.render(row) : truncate(raw, 120);
                    const dir = typeof raw === "string" ? textDir(raw) : "ltr";
                    return (
                      <td key={col.key} dir={dir}>
                        {content}
                      </td>
                    );
                  })}
                  {copyJsonEnabled ? (
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        void navigator.clipboard?.writeText(JSON.stringify(row, null, 2));
                      }}
                    >
                      Copy JSON
                    </button>
                  </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {showPagination && sorted.length > pageSize ? (
        <div className="table-pagination">
          <button type="button" className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page + 1} of {totalPages} · {sorted.length} rows</span>
          <button type="button" className="btn btn-ghost btn-sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      ) : null}
    </div>
  );
}
