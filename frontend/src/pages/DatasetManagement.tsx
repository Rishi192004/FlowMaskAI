import React, { useRef, useState } from 'react';
import { Check, Database, FileSpreadsheet, Play, Trash2, UploadCloud } from 'lucide-react';
import { datasetsApi } from '../../api/datasets';
import { DataTable } from '../../components/common/DataTable';
import { ErrorState } from '../../components/common/FeedbackStates';
import { StatusBadge } from '../../components/common/StatusBadge';
import { useFilters } from '../../context/FilterContext';
import { Dataset, DatasetUploadResponse } from '../../types/api';

interface DatasetManagementProps {
  onNavigateToETL?: () => void;
}

export const DatasetManagement: React.FC<DatasetManagementProps> = ({ onNavigateToETL }) => {
  const { datasets, selectedDatasetId, setSelectedDatasetId, refreshDatasets } = useFilters();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<DatasetUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Only CSV event log files are supported.');
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      const res = await datasetsApi.upload(file);
      setUploadResult(res);
      await refreshDatasets();
      setSelectedDatasetId(res.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to upload event log.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const columns = [
    {
      key: 'name',
      header: 'Dataset Name',
      render: (d: Dataset) => (
        <div>
          <div className="font-semibold text-slate-200 flex items-center gap-2">
            <span>{d.name}</span>
            {d.id === selectedDatasetId && (
              <span className="text-[10px] bg-blue-500/20 text-blue-400 font-mono px-1.5 py-0.5 rounded border border-blue-500/30">
                ACTIVE
              </span>
            )}
          </div>
          <span className="text-[11px] text-slate-500 font-mono">{d.filename}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (d: Dataset) => <StatusBadge status={d.status} />,
    },
    {
      key: 'total_rows_raw',
      header: 'Verified Events',
      render: (d: Dataset) => (
        <span className="font-mono text-slate-300">
          {d.total_rows_raw > 0 ? d.total_rows_raw.toLocaleString() : 'Pending ETL'}
        </span>
      ),
    },
    {
      key: 'file_size_bytes',
      header: 'File Size',
      render: (d: Dataset) => (
        <span className="font-mono text-slate-400">
          {(d.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Uploaded Date',
      render: (d: Dataset) => (
        <span className="text-slate-400">
          {new Date(d.created_at).toLocaleDateString()} {new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (d: Dataset) => (
        <div className="flex items-center gap-2">
          {d.id !== selectedDatasetId && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedDatasetId(d.id);
              }}
              className="px-2 py-1 bg-surface hover:bg-surface-hover text-slate-300 text-xs rounded border border-surface-border transition-colors"
            >
              Set Active
            </button>
          )}
          {d.status === 'uploaded' && onNavigateToETL && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedDatasetId(d.id);
                onNavigateToETL();
              }}
              className="flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded font-medium transition-colors"
            >
              <Play className="w-3 h-3" /> Process ETL
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">Dataset Management</h2>
        <p className="text-xs text-slate-400 mt-1">
          Ingest raw CSV business event logs, inspect detected schema columns, and manage active process logs.
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Upload Dropzone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-surface-border hover:border-blue-500/50 bg-surface-card/60 hover:bg-surface-card rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all group"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileUpload}
          className="hidden"
        />
        <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
          <UploadCloud className="w-6 h-6" />
        </div>
        <p className="text-sm font-semibold text-slate-200">
          {isUploading ? 'Validating and uploading event log...' : 'Click or drag CSV event log to upload'}
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Supports CSV files up to 50MB. Columns will be heuristically mapped for process mining.
        </p>
      </div>

      {/* Upload Preview Banner if just uploaded */}
      {uploadResult && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
              <Check className="w-4 h-4" />
              <span>Dataset '{uploadResult.name}' uploaded successfully ({uploadResult.detected_columns.length} columns detected)</span>
            </div>
            {onNavigateToETL && (
              <button
                onClick={onNavigateToETL}
                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-lg font-medium transition-colors"
              >
                Proceed to ETL Processing →
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] font-mono text-slate-300">
            <span className="text-slate-500">Suggested Mapping:</span>
            {Object.entries(uploadResult.suggested_mapping).map(([k, v]) => (
              <span key={k} className="px-2 py-0.5 bg-surface rounded border border-surface-border">
                {k} = <strong className="text-emerald-400">{v}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Datasets Table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <Database className="w-4 h-4 text-slate-400" />
          <span>Uploaded Event Logs ({datasets.length})</span>
        </h3>
        <DataTable
          columns={columns}
          data={datasets}
          searchKey="name"
          searchPlaceholder="Search datasets..."
          onRowClick={(d) => setSelectedDatasetId(d.id)}
          emptyMessage="No event logs uploaded yet. Upload your first CSV above."
        />
      </div>
    </div>
  );
};
