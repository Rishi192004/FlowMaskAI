import React, { useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, FileText, GitFork, Sparkles } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { processApi } from '../api/process';
import { DataTable } from '../components/common/DataTable';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import { ProcessVariantItem, ProcessVariantsResponse } from '../types/api';

export const VariantExplorer: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate, selectedDepartment, selectedVendor } = useFilters();
  const [variantsData, setVariantsData] = useState<ProcessVariantsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ProcessVariantItem | null>(null);

  const fetchVariants = async () => {
    if (!selectedDatasetId) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const res = await processApi.getVariants({
        dataset_id: selectedDatasetId,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        department: selectedDepartment || undefined,
        vendor_id: selectedVendor || undefined,
      });
      setVariantsData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch process variants.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVariants();
  }, [selectedDatasetId, startDate, endDate, selectedDepartment, selectedVendor]);

  if (!selectedDataset) {
    return <EmptyState title="No Dataset Selected" description="Select a dataset to explore process execution variants." />;
  }

  if (isLoading) {
    return <LoadingState message="Discovering unique process paths and analyzing variants..." />;
  }

  if (error || !variantsData) {
    return <ErrorState message={error || 'Failed to load process variants.'} onRetry={fetchVariants} />;
  }

  const chartData = variantsData.variants.slice(0, 8).map(v => ({
    name: `Variant #${v.variant_id}`,
    cases: v.case_count,
    percentage: v.percentage,
  }));

  const variantColumns = [
    {
      key: 'variant_id',
      header: 'Variant',
      render: (v: ProcessVariantItem) => (
        <span className="font-mono text-slate-300 font-semibold">#{v.variant_id}</span>
      ),
      width: '80px',
    },
    {
      key: 'variant_signature',
      header: 'Activity Execution Path',
      render: (v: ProcessVariantItem) => (
        <div>
          <div className="font-mono text-xs text-slate-200 font-semibold">{v.variant_signature}</div>
          <div className="text-[11px] text-slate-500 font-mono mt-0.5">
            Sample Cases: {v.sample_case_ids.join(', ')}
          </div>
        </div>
      ),
    },
    {
      key: 'case_count',
      header: 'Cases',
      render: (v: ProcessVariantItem) => (
        <span className="font-mono text-slate-300">{v.case_count.toLocaleString()}</span>
      ),
      width: '100px',
    },
    {
      key: 'percentage',
      header: 'Volume Share',
      render: (v: ProcessVariantItem) => (
        <span className="font-mono text-blue-400 font-semibold">{v.percentage}%</span>
      ),
      width: '110px',
    },
    {
      key: 'is_rare',
      header: 'Classification',
      render: (v: ProcessVariantItem) => (
        <StatusBadge status={v.is_rare ? 'Rare Path' : 'Standard'} size="sm" />
      ),
      width: '120px',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">Process Variant Explorer</h2>
        <p className="text-xs text-slate-400 mt-1">
          Inspect distinct trace execution sequences, identify common standards vs rare outlier paths.
        </p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Distinct Variants"
          value={variantsData.unique_variants_count}
          subtext="Unique execution sequences"
          icon={<GitFork className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Top Variant Coverage"
          value={`${variantsData.top_variant_percentage}%`}
          subtext="Cases following the happy path"
          icon={<Sparkles className="w-4 h-4 text-emerald-400" />}
          badge={{ text: 'Standard', variant: 'success' }}
        />
        <MetricCard
          title="Rare Execution Paths"
          value={variantsData.variants.filter(v => v.is_rare).length}
          subtext="Variants with <3% case volume"
          icon={<AlertCircle className="w-4 h-4 text-amber-400" />}
          badge={{ text: 'Outliers', variant: 'warning' }}
        />
        <MetricCard
          title="Excessive Activity Cases"
          value={variantsData.excessive_activity_cases.length}
          subtext="Cases with significant loop rework"
          icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
          badge={{ text: variantsData.excessive_activity_cases.length > 0 ? 'Review' : 'None', variant: 'danger' }}
        />
      </div>

      {/* Variant Distribution Chart */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Top Variant Distribution</h3>
            <p className="text-xs text-slate-400">Relative volume percentage for top discovered paths</p>
          </div>
          <span className="text-xs font-mono text-slate-400">Pareto Distribution</span>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis dataKey="name" stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" />
              <YAxis stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
              />
              <Bar dataKey="percentage" name="Case %" fill="#3B82F6" radius={[4, 4, 0, 0]}>
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={index === 0 ? '#10B981' : '#3B82F6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Excessive Activities Alert Table if any */}
      {variantsData.excessive_activity_cases.length > 0 && (
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 text-rose-400 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>Cases with Excessive Activity Counts (Rework / Infinite Loops)</span>
          </div>
          <div className="space-y-2">
            {variantsData.excessive_activity_cases.slice(0, 5).map(c => (
              <div key={c.case_id} className="p-3 bg-surface border border-surface-border rounded-lg flex items-center justify-between text-xs">
                <span className="font-mono text-slate-200 font-semibold">{c.case_id}</span>
                <span className="text-slate-400">{c.reason}</span>
                <span className="font-mono font-semibold text-rose-400">{c.event_count} events</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Process Variants Table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-400" />
          <span>All Discovered Process Variants ({variantsData.variants.length})</span>
        </h3>
        <DataTable
          columns={variantColumns}
          data={variantsData.variants}
          searchKey="variant_signature"
          searchPlaceholder="Search execution paths..."
          pageSize={10}
        />
      </div>
    </div>
  );
};
