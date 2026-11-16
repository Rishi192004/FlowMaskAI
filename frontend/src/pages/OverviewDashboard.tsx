import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  Repeat,
  TrendingUp,
} from 'lucide-react';
import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { analyticsApi } from '../../api/analytics';
import { processApi } from '../../api/process';
import { EmptyState, ErrorState, LoadingState } from '../../components/common/FeedbackStates';
import { MetricCard } from '../../components/common/MetricCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { useFilters } from '../../context/FilterContext';
import { BottlenecksResponse, OverviewMetrics, ProcessVariantsResponse, TrendsResponse } from '../../types/api';

export const OverviewDashboard: React.FC = () => {
  const { selectedDatasetId, startDate, endDate } = useFilters();
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [bottlenecks, setBottlenecks] = useState<BottlenecksResponse | null>(null);
  const [variants, setVariants] = useState<ProcessVariantsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    if (!selectedDatasetId) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const params = {
        dataset_id: selectedDatasetId,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };

      const [ovData, trData, bnData, varData] = await Promise.all([
        analyticsApi.getOverview(params),
        analyticsApi.getTrends(params),
        analyticsApi.getBottlenecks(params),
        processApi.getVariants(params),
      ]);

      setOverview(ovData);
      setTrends(trData);
      setBottlenecks(bnData);
      setVariants(varData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load overview analytics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [selectedDatasetId, startDate, endDate]);

  if (!selectedDatasetId) {
    return (
      <EmptyState
        title="No Dataset Selected"
        description="Please select or upload a Purchase-to-Pay event log from the Dataset Management page."
      />
    );
  }

  if (isLoading) {
    return <LoadingState message="Computing operational KPIs and process mining metrics..." />;
  }

  if (error || !overview) {
    return <ErrorState message={error || 'Unable to retrieve dashboard metrics.'} onRetry={fetchDashboardData} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">Operational Overview</h2>
        <p className="text-xs text-slate-400 mt-1">
          Real-time process mining KPIs and operational metrics calculated from verified event logs.
        </p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Purchase Cases"
          value={overview.total_purchase_cases.toLocaleString()}
          subtext={`${overview.total_events.toLocaleString()} total verified events`}
          icon={<FileText className="w-4 h-4 text-blue-400" />}
          badge={{ text: `${(overview.completion_rate * 100).toFixed(1)}% Completed`, variant: 'info' }}
        />
        <MetricCard
          title="Avg Cycle Time"
          value={`${overview.avg_cycle_time_hours.toFixed(1)}h`}
          subtext={`Median: ${overview.median_cycle_time_hours.toFixed(1)}h | P90: ${overview.p90_cycle_time_hours.toFixed(1)}h`}
          icon={<Clock className="w-4 h-4 text-emerald-400" />}
          badge={{
            text: overview.avg_cycle_time_hours <= overview.sla_hours ? 'Within SLA' : 'Exceeds SLA',
            variant: overview.avg_cycle_time_hours <= overview.sla_hours ? 'success' : 'danger',
          }}
        />
        <MetricCard
          title="Rework Rate"
          value={`${(overview.rework_percentage * 100).toFixed(1)}%`}
          subtext={`${overview.rework_cases.toLocaleString()} cases with repeated steps`}
          icon={<Repeat className="w-4 h-4 text-amber-400" />}
          badge={{
            text: overview.rework_percentage > 0.1 ? 'High Rework' : 'Normal',
            variant: overview.rework_percentage > 0.1 ? 'warning' : 'success',
          }}
        />
        <MetricCard
          title="SLA Breach Rate"
          value={`${(overview.sla_breach_percentage * 100).toFixed(1)}%`}
          subtext={`${overview.sla_breach_cases.toLocaleString()} cases breached ${overview.sla_hours}h SLA`}
          icon={<AlertOctagon className="w-4 h-4 text-rose-400" />}
          badge={{
            text: overview.sla_breach_percentage > 0.15 ? 'Critical' : 'Acceptable',
            variant: overview.sla_breach_percentage > 0.15 ? 'danger' : 'neutral',
          }}
        />
      </div>

      {/* Second Row KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="Completed vs. Incomplete"
          value={`${overview.completed_cases.toLocaleString()} / ${overview.incomplete_cases.toLocaleString()}`}
          subtext="Incomplete cases are strictly separated from finished workflows"
          icon={<CheckCircle className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Total Processed Spend"
          value={`$${(overview.total_spend_usd / 1000).toFixed(1)}k`}
          subtext="Total transaction volume captured in event log"
          icon={<DollarSign className="w-4 h-4 text-emerald-400" />}
        />
        <MetricCard
          title="Top Process Variant Coverage"
          value={`${variants?.top_variant_percentage.toFixed(1) || '0.0'}%`}
          subtext={`Across ${variants?.unique_variants_count || 0} unique execution paths`}
          icon={<TrendingUp className="w-4 h-4 text-indigo-400" />}
        />
      </div>

      {/* Monthly Trends & Volume Chart */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Transaction Volume & Cycle Time Trends</h3>
            <p className="text-xs text-slate-400">Monthly progression of case counts vs average duration</p>
          </div>
          <span className="text-xs font-mono text-slate-400">SQL Grouped Aggregation</span>
        </div>

        <div className="h-72 w-full">
          {trends && trends.trends.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trends.trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="month" stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" />
                <YAxis yAxisId="left" stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" />
                <YAxis yAxisId="right" orientation="right" stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" unit="h" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar yAxisId="left" dataKey="case_volume" name="Case Volume" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="avg_cycle_time_hours" name="Avg Cycle Time (h)" stroke="#10B981" strokeWidth={2} dot={{ r: 4 }} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
              Insufficient historical data points for monthly aggregation.
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: Major Bottlenecks & Top Variants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Major Bottlenecks */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-100">Operational Bottlenecks</h3>
              <p className="text-xs text-slate-400">Activities with highest queue delay and rework</p>
            </div>
            <StatusBadge status="Explainable Ranking" size="sm" />
          </div>

          <div className="space-y-3">
            {bottlenecks && bottlenecks.bottlenecks.length > 0 ? (
              bottlenecks.bottlenecks.slice(0, 4).map(b => (
                <div key={b.activity} className="p-3 bg-surface border border-surface-border rounded-lg flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-400">#{b.rank}</span>
                      <h4 className="text-xs font-semibold text-slate-200">{b.activity}</h4>
                      {b.rework_rate > 0.05 && <StatusBadge status="Rework Loop" size="sm" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{b.reasons[0]}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-semibold text-rose-400">{b.avg_waiting_time_hours}h</span>
                    <p className="text-[10px] text-slate-500 font-mono">{b.transition_count} transitions</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No major bottlenecks identified.</p>
            )}
          </div>
        </div>

        {/* Top Process Variants */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-100">Top Process Execution Paths</h3>
              <p className="text-xs text-slate-400">Most frequent trace variants discovered</p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {variants?.unique_variants_count || 0} Total Variants
            </span>
          </div>

          <div className="space-y-3">
            {variants && variants.variants.length > 0 ? (
              variants.variants.slice(0, 4).map(v => (
                <div key={v.variant_id} className="p-3 bg-surface border border-surface-border rounded-lg">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-semibold text-slate-200">Variant #{v.variant_id}</span>
                    <span className="font-mono text-blue-400 font-semibold">{v.percentage}% ({v.case_count} cases)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-mono truncate" title={v.variant_signature}>
                    {v.variant_signature}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No process variants discovered yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
