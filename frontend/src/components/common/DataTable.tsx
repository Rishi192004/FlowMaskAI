import React, { useState } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  searchKey?: keyof T;
  searchPlaceholder?: string;
  pageSize?: number;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  searchKey,
  searchPlaceholder = 'Search records...',
  pageSize = 10,
  onRowClick,
  emptyMessage = 'No records found.',
}: DataTableProps<T>) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filteredData = searchKey && search.trim()
    ? data.filter(item => {
        const val = item[searchKey];
        return val ? String(val).toLowerCase().includes(search.toLowerCase()) : false;
      })
    : data;

  const totalPages = Math.ceil(filteredData.length / pageSize) || 1;
  const paginatedData = filteredData.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden">
      {searchKey && (
        <div className="p-4 border-b border-surface-border flex items-center justify-between">
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={search}
            onChange={e => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full max-w-xs px-3 py-1.5 bg-surface border border-surface-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-primary"
          />
          <span className="text-xs text-slate-500 font-mono">
            {filteredData.length} records
          </span>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface/50 border-b border-surface-border text-slate-400 uppercase tracking-wider font-medium text-[11px]">
            <tr>
              {columns.map(col => (
                <th key={col.key} className="py-3 px-4 font-semibold" style={{ width: col.width }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border/50 text-slate-300">
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-8 text-center text-slate-500">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((item, idx) => (
                <tr
                  key={idx}
                  onClick={() => onRowClick && onRowClick(item)}
                  className={`hover:bg-surface-hover/60 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
                >
                  {columns.map(col => (
                    <td key={col.key} className="py-3 px-4">
                      {col.render ? col.render(item) : String(item[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="p-3 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-2.5 py-1 bg-surface border border-surface-border rounded hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-2.5 py-1 bg-surface border border-surface-border rounded hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
