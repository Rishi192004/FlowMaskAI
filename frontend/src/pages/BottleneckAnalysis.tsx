import React, { useEffect, useState } from 'react';
import { AlertTriangle, Clock, HelpCircle, Layers, Timer, TrendingUp } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { analyticsApi } from '../api/analytics';
import { DataTable } from '../components/common/DataTable';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import { BottleneckItem, BottlenecksResponse, WaitingTimeMetrics } from '../types/api';

export const BottleneckAnalysis: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate } = useFilters();
  const [bottlenecksData, setBottlenecksData] = useState<BottlenecksResponse | null>(null);
  const [waitingData, setWaitingData] = useState<WaitingTimeMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBottlenecks = async () => {
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
        activity_sla_hours: 48.0,
      };

      const [bnRes, wtRes] = await Promise.all([
        analyticsApi.getBottlenecks(params),
        analyticsApi.getWaitingTime(params),
      ]);

      setBottlenecksData(bnRes);
      setWaitingData(wtRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to analyze process bottlenecks.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBottlenecks();
  }, [selectedDatasetId, startDate, endDate]);

  if (!selectedDataset) {
    return <EmptyState title="No Dataset Selected" description="Select a dataset to identify process queue bottlenecks." />;
  }

  if (isLoading) {
    return <LoadingState message="Calculating activity waiting times and ranking queue bottlenecks..." />;
  }

  if (error || !bottlenecksData) {
    return <ErrorState message={error || 'Failed to load bottleneck analytics.'} onRetry={fetchBottlenecks} />;
  }

  const chartData = (waitingData?.activities || []).map(a => ({
    name: a.activity,
    avg: a.avg_waiting_time_hours,
    median: a.median_waiting_time_hours,
  }));

  const columns = [
    {
      key: 'rank',
      header: 'Rank',
      render: (b: BottleneckItem) => (
        <span className={`font-mono font-bold text-xs ${
          b.rank === 1 ? 'text-rose-400' : b.rank === 2 ? 'text-amber-400' : 'text-slate-400'
        }`}>
          #{b.rank}
        </span>
      ),
      width: '70px',
    },
    {
      key: 'activity',
      header: 'Activity',
      render: (b: BottleneckItem) => (
        <div>
          <div className="font-semibold text-slate-200 text-xs">{b.activity}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{b.reasons[0]}</div>
        </div>
      ),
    },
    {
      key: 'bottleneck_score',
      header: 'Score',
      render: (b: BottleneckItem) => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-surface rounded-full overflow-hidden border border-surface-border">
            <div
              className={`h-full ${b.bottleneck_score > 60 ? 'bg-rose-500' : b.bottleneck_score > 30 ? 'bg-amber-500' : 'bg-blue-500'}`}
              style={{ width: `${Math.min(100, b.bottleneck_score)}%` }}
            />
          </div>
          <span className="font-mono text-xs font-semibold text-slate-200">{b.bottleneck_score.toFixed(1)}</span>
        </div>
      ),
      width: '140px',
    },
    {
      key: 'avg_waiting_time_hours',
      header: 'Avg Wait',
      render: (b: BottleneckItem) => (
        <span className="font-mono text-slate-300 text-xs">{b.avg_waiting_time_hours.toFixed(1)}h</span>
      ),
      width: '90px',
    },
    {
      key: 'median_waiting_time_hours',
      header: 'Median Wait',
      render: (b: BottleneckItem) => (
        <span className="font-mono text-slate-400 text-xs">{b.median_waiting_time_hours.toFixed(1)}h</span>
      ),
      width: '100px',
    },
    {
      key: 'rework_rate',
      header: 'Rework Rate',
      render: (b: BottleneckItem) => (
        <span className={`font-mono text-xs ${b.rework_rate > 0.05 ? 'text-amber-400 font-semibold' : 'text-slate-400'}`}>
          {(b.rework_rate * 100).toFixed(1)}%
        </span>
      ),
      width: '100px',
    },
    {
      key: 'sla_breach_rate',
      header: 'Transition SLA Breach',
      render: (b: BottleneckItem) => (
        <span className={`font-mono text-xs ${b.sla_breach_rate > 0.1 ? 'text-rose-400 font-semibold' : 'text-slate-400'}`}>
          {(b.sla_breach_rate * 100).toFixed(1)}%
        </span>
      ),
      width: '160px',
    },
  ];

  const topBottleneck = bottlenecksData.bottlenecks[0];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100">Bottleneck Analysis</h2>
        <p className="text-xs text-slate-400 mt-1">
          Identify process steps with the longest queue delay, rework repetition loops, and transition SLA breaches.
        </p>
      </div>

      {/* Top Banner KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="Primary Bottleneck"
          value={topBottleneck?.activity || 'None Detected'}
          subtext={topBottleneck ? `Avg wait: ${topBottleneck.avg_waiting_time_hours}h across ${topBottleneck.transition_count} transitions` : ''}
          icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
          badge={{ text: 'Rank #1', variant: 'danger' }}
        />
        <MetricCard
          title="Overall Avg Wait Time"
          value={`${waitingData?.overall_avg_waiting_time_hours.toFixed(1) || '0.0'}h`}
          subtext="Queue delay across all consecutive transitions"
          icon={<Clock className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Ranking Methodology"
          value="Composite Multi-Factor"
          subtext="Weighted: Wait Time (40%), Median (20%), Rework (20%), SLA (20%)"
          icon={<Timer className="w-4 h-4 text-emerald-400" />}
        />
      </div>

      {/* Waiting Time Comparison Chart */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Activity Queue Delay Comparison</h3>
            <p className="text-xs text-slate-400">Average vs. Median waiting time before activity execution (hours)</p>
          </div>
          <span className="text-xs font-mono text-slate-400">SQL LAG() Aggregation</span>
        </div>

        <div className="h-64 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="name" stroke="#64748B" fontSize={10} fontFamily="JetBrains Mono" interval={0} angle={-15} textAnchor="end" height={50} />
                <YAxis stroke="#64748B" fontSize={11} fontFamily="JetBrains Mono" unit="h" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="avg" name="Average Waiting Time (h)" fill="#EF4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="median" name="Median Waiting Time (h)" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
              No transition data available.
            </div>
          )}
        </div>
      </div>

      {/* Bottlenecks Table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <Timer className="w-4 h-4 text-slate-400" />
          <span>Ranked Bottlenecks ({bottlenecksData.bottlenecks.length})</span>
        </h3>
        <DataTable
          columns={columns}
          data={bottlenecksData.bottlenecks}
          searchKey="activity"
          searchPlaceholder="Search activities..."
        />
      </div>
    </div>
  );
};
