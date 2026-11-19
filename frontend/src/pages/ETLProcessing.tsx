import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, FileSpreadsheet, Play, Settings2 } from 'lucide-react';
import { datasetsApi } from '../api/datasets';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';

interface ETLProcessingProps {
  onNavigateToQuality?: () => void;
}

export const ETLProcessing: React.FC<ETLProcessingProps> = ({ onNavigateToQuality }) => {
  const { selectedDatasetId, selectedDataset, refreshDatasets } = useFilters();
  const [normalizeActivities, setNormalizeActivities] = useState(true);
  const [dropDuplicates, setDropDuplicates] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunETL = async () => {
    if (!selectedDatasetId) return;
    try {
      setIsProcessing(true);
      setError(null);
      const res = await datasetsApi.process(selectedDatasetId, {
        normalize_activities: normalizeActivities,
        drop_duplicates: dropDuplicates,
      });
      setProcessResult(res);
      await refreshDatasets();
    } catch (err: any) {
      setError(err?.message || 'ETL processing failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!selectedDataset) {
    return (
      <EmptyState
        title="No Dataset Selected"
        description="Select a dataset from the header or upload a CSV in Dataset Management."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">ETL & Data Transformation</h2>
        <p className="text-xs text-slate-400 mt-1">
          Extract, normalize timestamps and activity names, validate case sequences, and populate typed PostgreSQL tables.
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={handleRunETL} />}

      {/* Dataset Overview Bar */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-xl flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">{selectedDataset.name}</h3>
            <StatusBadge status={selectedDataset.status} size="sm" />
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            {selectedDataset.filename} • Delimiter: '{selectedDataset.delimiter}' • Size: {(selectedDataset.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
          </p>
        </div>

        <button
          onClick={handleRunETL}
          disabled={isProcessing}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
        >
          <Play className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
          {isProcessing ? 'Executing ETL Pipeline...' : 'Run ETL Pipeline'}
        </button>
      </div>

      {/* Transformation Configuration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Settings2 className="w-4 h-4 text-slate-400" />
            <span>Transformation Controls</span>
          </div>

          <div className="space-y-3">
            <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer hover:bg-surface-hover/80 transition-colors">
              <input
                type="checkbox"
                checked={normalizeActivities}
                onChange={e => setNormalizeActivities(e.target.checked)}
                className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-xs font-semibold text-slate-200">Normalize Activity Names</span>
                <p className="text-[11px] text-slate-400">
                  Standardizes casing, strips whitespace, and preserves standard acronyms (e.g., 'po_created' → 'PO Created').
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer hover:bg-surface-hover/80 transition-colors">
              <input
                type="checkbox"
                checked={dropDuplicates}
                onChange={e => setDropDuplicates(e.target.checked)}
                className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-xs font-semibold text-slate-200">Filter Duplicate Events</span>
                <p className="text-[11px] text-slate-400">
                  Filters identical (case, activity, timestamp, resource) events from cleaned tables while logging them for quality auditing.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Column Mapping Preview */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="text-sm font-semibold text-slate-200">Active Column Mappings</div>
          <div className="space-y-2 text-xs font-mono">
            {selectedDataset.column_mapping ? (
              Object.entries(selectedDataset.column_mapping).map(([canonical, csvCol]) => (
                <div key={canonical} className="p-2.5 bg-surface border border-surface-border rounded-lg flex items-center justify-between">
                  <span className="text-slate-400">{canonical}</span>
                  <span className="text-blue-400 font-semibold">{csvCol}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 font-sans">No column mapping detected yet.</p>
            )}
          </div>
        </div>
      </div>

      {/* Execution Results Banner */}
      {processResult && (
        <div className="p-5 bg-surface-card border border-surface-border rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-100">ETL Pipeline Completed</h3>
              <span className="text-xs font-mono text-emerald-400 font-semibold">({processResult.duration_seconds}s)</span>
            </div>
            {onNavigateToQuality && (
              <button
                onClick={onNavigateToQuality}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface-hover text-slate-200 rounded-lg text-xs font-medium border border-surface-border transition-colors"
              >
                <span>View Quality Report</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard
              title="Received Records"
              value={processResult.metrics.total_records_received.toLocaleString()}
            />
            <MetricCard
              title="Loaded Records"
              value={processResult.metrics.records_loaded.toLocaleString()}
              badge={{ text: 'Verified', variant: 'success' }}
            />
            <MetricCard
              title="Duplicate Records"
              value={processResult.metrics.duplicate_records.toLocaleString()}
              badge={{ text: 'Audited', variant: 'warning' }}
            />
            <MetricCard
              title="Rejected Records"
              value={processResult.metrics.records_rejected.toLocaleString()}
              badge={{ text: 'Logged', variant: 'danger' }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
