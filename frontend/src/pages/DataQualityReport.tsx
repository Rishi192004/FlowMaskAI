import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, Database, FileText, ShieldAlert, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { datasetsApi } from '../api/datasets';
import { DataTable } from '../components/common/DataTable';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import { DataQualityIssueItem, DataQualityReport } from '../types/api';

export const DataQualityReportPage: React.FC = () => {
  const { selectedDatasetId, selectedDataset } = useFilters();
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQualityData = async () => {
    if (!selectedDatasetId) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const res = await datasetsApi.getQuality(selectedDatasetId);
      setReport(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load data quality report.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQualityData();
  }, [selectedDatasetId]);

  if (!selectedDataset) {
    return <EmptyState title="No Dataset Selected" description="Select a dataset to view its ETL data quality audit." />;
  }

  if (isLoading) {
    return <LoadingState message="Compiling data quality metrics and issue logs..." />;
  }

  if (error || !report) {
    return <ErrorState message={error || 'Failed to load report.'} onRetry={fetchQualityData} />;
  }

  const chartData = Object.entries(report.issue_breakdown).map(([issue_type, count]) => ({
    name: issue_type.replace(/_/g, ' '),
    count,
  }));

  const issueColumns = [
    {
      key: 'row_index',
      header: 'Row #',
      render: (i: DataQualityIssueItem) => <span className="font-mono text-slate-400">#{i.row_index}</span>,
      width: '80px',
    },
    {
      key: 'issue_type',
      header: 'Anomaly Type',
      render: (i: DataQualityIssueItem) => (
        <span className="font-semibold text-slate-200 font-mono text-[11px]">{i.issue_type}</span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (i: DataQualityIssueItem) => <StatusBadge status={i.severity} size="sm" />,
      width: '90px',
    },
    {
      key: 'details',
      header: 'Diagnostic Details',
      render: (i: DataQualityIssueItem) => (
        <span className="font-mono text-[11px] text-slate-400">{JSON.stringify(i.details)}</span>
      ),
    },
    {
      key: 'is_fatal',
      header: 'Action Taken',
      render: (i: DataQualityIssueItem) => (
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
          i.is_fatal ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        }`}>
          {i.is_fatal ? 'REJECTED' : 'FLAGGED & LOADED'}
        </span>
      ),
      width: '130px',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">Data Quality & Ingestion Audit</h2>
        <p className="text-xs text-slate-400 mt-1">
          Complete accounting of all ingested records: validation, normalization, and row-level anomaly auditing.
        </p>
      </div>

      {/* Record Accounting Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Received"
          value={report.metrics.total_records_received.toLocaleString()}
          subtext="Total rows parsed from raw CSV"
          icon={<Database className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Successfully Loaded"
          value={report.metrics.records_loaded.toLocaleString()}
          subtext={`${((report.metrics.records_loaded / (report.metrics.total_records_received || 1)) * 100).toFixed(1)}% loaded into DB`}
          icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
          badge={{ text: 'Verified', variant: 'success' }}
        />
        <MetricCard
          title="Duplicate Events"
          value={report.metrics.duplicate_records.toLocaleString()}
          subtext="Duplicate (case, activity, time) events"
          icon={<AlertTriangle className="w-4 h-4 text-amber-400" />}
          badge={{ text: 'Audited', variant: 'warning' }}
        />
        <MetricCard
          title="Records Rejected"
          value={report.metrics.records_rejected.toLocaleString()}
          subtext="Malformed dates or missing case/activity"
          icon={<ShieldAlert className="w-4 h-4 text-rose-400" />}
          badge={{ text: report.metrics.records_rejected > 0 ? 'Logged' : 'Clean', variant: report.metrics.records_rejected > 0 ? 'danger' : 'success' }}
        />
      </div>

      {/* Anomaly Breakdown Chart */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Quality Issues Breakdown</h3>
            <p className="text-xs text-slate-400">Categorized count of identified data quality anomalies</p>
          </div>
          <span className="text-xs font-mono text-slate-400">100% Traceable</span>
        </div>

        <div className="h-56 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
                <XAxis type="number" stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" />
                <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={11} width={180} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Count" fill="#F59E0B" radius={[0, 4, 4, 0]}>
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#EF4444' : '#F59E0B'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-emerald-400 font-mono">
              ✓ Zero data quality issues detected in this event log.
            </div>
          )}
        </div>
      </div>

      {/* Anomaly Issues Table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-400" />
          <span>Diagnostic Issue Audit Log ({report.recent_issues.length} displayed)</span>
        </h3>
        <DataTable
          columns={issueColumns}
          data={report.recent_issues}
          searchKey="issue_type"
          searchPlaceholder="Filter by issue type..."
          emptyMessage="No issues logged for this dataset."
        />
      </div>
    </div>
  );
};
