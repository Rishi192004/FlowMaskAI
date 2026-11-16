import React from 'react';
import { Calendar, Database, Filter, RefreshCw, X } from 'lucide-react';
import { useFilters } from '../../context/FilterContext';

export const Header: React.FC = () => {
  const {
    datasets,
    selectedDatasetId,
    selectedDataset,
    setSelectedDatasetId,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    selectedDepartment,
    setSelectedDepartment,
    selectedVendor,
    setSelectedVendor,
    isLoadingDatasets,
    refreshDatasets,
  } = useFilters();

  const hasActiveFilters = Boolean(startDate || endDate || selectedDepartment || selectedVendor);

  const clearFilters = () => {
    setStartDate('');
    setEndDate('');
    setSelectedDepartment('');
    setSelectedVendor('');
  };

  return (
    <header className="h-16 bg-surface border-b border-surface-border px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
      {/* Left: Active Dataset Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span>Active Dataset:</span>
        </div>
        <div className="relative">
          <select
            value={selectedDatasetId || ''}
            onChange={e => setSelectedDatasetId(e.target.value || null)}
            disabled={isLoadingDatasets || datasets.length === 0}
            className="bg-surface-card border border-surface-border text-xs text-slate-100 rounded-lg px-3 py-1.5 pr-8 focus:outline-none focus:border-blue-500 appearance-none font-medium cursor-pointer"
          >
            {datasets.length === 0 ? (
              <option value="">No datasets uploaded</option>
            ) : (
              datasets.map(d => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.total_rows_raw > 0 ? `${d.total_rows_raw.toLocaleString()} rows` : d.status})
                </option>
              ))
            )}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
            ▼
          </div>
        </div>

        <button
          onClick={() => refreshDatasets()}
          disabled={isLoadingDatasets}
          title="Refresh datasets"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-hover rounded-lg transition-colors border border-surface-border"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDatasets ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Right: Global Operational Filters */}
      <div className="flex items-center gap-3">
        {/* Date Filters */}
        <div className="flex items-center gap-1.5 bg-surface-card border border-surface-border rounded-lg px-2.5 py-1 text-xs text-slate-300">
          <Calendar className="w-3.5 h-3.5 text-slate-500" />
          <input
            type="date"
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            className="bg-transparent text-slate-200 focus:outline-none text-xs"
            title="Start date filter"
          />
          <span className="text-slate-600">→</span>
          <input
            type="date"
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            className="bg-transparent text-slate-200 focus:outline-none text-xs"
            title="End date filter"
          />
        </div>

        {/* Department Filter */}
        <select
          value={selectedDepartment}
          onChange={e => setSelectedDepartment(e.target.value)}
          className="bg-surface-card border border-surface-border text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Departments</option>
          <option value="Procurement">Procurement</option>
          <option value="Finance">Finance</option>
          <option value="Supply Chain">Supply Chain</option>
          <option value="IT Ops">IT Ops</option>
          <option value="Marketing">Marketing</option>
          <option value="Legal">Legal</option>
        </select>

        {/* Vendor Filter */}
        <input
          type="text"
          placeholder="Filter Vendor..."
          value={selectedVendor}
          onChange={e => setSelectedVendor(e.target.value)}
          className="bg-surface-card border border-surface-border text-xs text-slate-200 placeholder-slate-500 rounded-lg px-2.5 py-1.5 w-28 focus:outline-none focus:border-blue-500"
        />

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-[11px] text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 px-2 py-1.5 rounded-lg border border-amber-500/20 transition-colors"
          >
            <X className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>
    </header>
  );
};
