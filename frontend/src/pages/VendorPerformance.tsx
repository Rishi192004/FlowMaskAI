import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  DollarSign,
  Search,
  ShieldAlert,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { analyticsApi } from '../api/analytics';
import { Column, DataTable } from '../components/common/DataTable';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import { VendorPerformanceItem, VendorPerformanceResponse } from '../types/api';

export const VendorPerformance: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate, selectedVendor } = useFilters();
  const [data, setData] = useState<VendorPerformanceResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSort, setSelectedSort] = useState<'spend' | 'cases' | 'cycle_time' | 'sla'>('spend');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVendorData = async () => {
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
        sla_hours: 720.0,
      };

      const res = await analyticsApi.getVendorPerformance(params);
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch vendor performance analytics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVendorData();
  }, [selectedDatasetId, startDate, endDate]);

  if (!selectedDataset) {
    return (
      <EmptyState
        title="No Dataset Selected"
        description="Select an active dataset in the top header to inspect vendor performance analytics."
      />
    );
  }

  if (isLoading) {
    return <LoadingState message="Aggregating multidimensional vendor performance metrics..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Vendor Analytics Failed"
        message={error}
        onRetry={fetchVendorData}
      />
    );
  }

  const vendors = data?.vendors || [];
  if (vendors.length === 0) {
    return (
      <EmptyState
        title="No Vendor Data Available"
        description="The selected dataset does not contain vendor attributes or matching records."
      />
    );
  }

  function round(val: number, decimals: number = 2): number {
    return Number(val.toFixed(decimals));
  }

  // Summary Metrics
  const totalVendors = vendors.length;
  const totalSpend = vendors.reduce((acc: number, v: VendorPerformanceItem) => acc + v.total_spend_usd, 0);
  const totalCases = vendors.reduce((acc: number, v: VendorPerformanceItem) => acc + v.total_cases, 0);
  const avgCycleTime = totalCases > 0
    ? round(vendors.reduce((acc: number, v: VendorPerformanceItem) => acc + (v.avg_cycle_time_hours * v.total_cases), 0) / totalCases, 1)
    : 0;
  const totalBreaches = vendors.reduce((acc: number, v: VendorPerformanceItem) => acc + v.sla_breach_count, 0);
  const overallBreachRate = totalCases > 0 ? round((totalBreaches / totalCases) * 100, 1) : 0;

  const topVendorBySpend = [...vendors].sort((a, b) => b.total_spend_usd - a.total_spend_usd)[0];

  // Filtering & Sorting
  const filteredVendors = vendors.filter((v: VendorPerformanceItem) =>
    v.vendor_id.toLowerCase().includes(searchQuery.toLowerCase().trim())
  );

  const sortedVendors = [...filteredVendors].sort((a, b) => {
    if (selectedSort === 'spend') return b.total_spend_usd - a.total_spend_usd;
    if (selectedSort === 'cases') return b.total_cases - a.total_cases;
    if (selectedSort === 'cycle_time') return b.avg_cycle_time_hours - a.avg_cycle_time_hours;
    if (selectedSort === 'sla') return b.sla_breach_rate - a.sla_breach_rate;
    return 0;
  });

  // Chart datasets (Top 10 by Spend)
  const top10Spend = [...vendors]
    .sort((a, b) => b.total_spend_usd - a.total_spend_usd)
    .slice(0, 10);

  // Top 10 by Cycle Time
  const top10Cycle = [...vendors]
    .filter(v => v.total_cases >= 3)
    .sort((a, b) => b.avg_cycle_time_hours - a.avg_cycle_time_hours)
    .slice(0, 10);

  const columns: Column<VendorPerformanceItem>[] = [
    {
      key: 'vendor_id',
      header: 'Vendor ID',
      render: (v: VendorPerformanceItem) => (
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-blue-400" />
          <span className="font-semibold text-slate-100 font-mono text-xs">{v.vendor_id}</span>
          {selectedVendor === v.vendor_id && (
            <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded font-mono">
              FILTERED
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'total_cases',
      header: 'Cases',
      render: (v: VendorPerformanceItem) => (
        <span className="font-mono text-slate-200">{v.total_cases.toLocaleString()}</span>
      ),
    },
    {
      key: 'total_spend_usd',
      header: 'Total Spend (USD)',
      render: (v: VendorPerformanceItem) => (
        <span className="font-mono font-medium text-emerald-400">
          ${v.total_spend_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      key: 'avg_cycle_time_hours',
      header: 'Avg Cycle (Hrs)',
      render: (v: VendorPerformanceItem) => (
        <span className="font-mono text-slate-200">{v.avg_cycle_time_hours.toFixed(1)}h</span>
      ),
    },
    {
      key: 'median_cycle_time_hours',
      header: 'Median (Hrs)',
      render: (v: VendorPerformanceItem) => (
        <span className="font-mono text-slate-400">{v.median_cycle_time_hours.toFixed(1)}h</span>
      ),
    },
    {
      key: 'sla_breach_rate',
      header: 'SLA Breach Rate',
      render: (v: VendorPerformanceItem) => {
        const pct = v.sla_breach_rate * 100;
        const color = pct > 20 ? 'text-rose-400 font-semibold' : pct > 10 ? 'text-amber-400' : 'text-slate-300';
        return (
          <span className={`font-mono ${color}`}>
            {pct.toFixed(1)}% ({v.sla_breach_count})
          </span>
        );
      },
    },
    {
      key: 'completion_rate',
      header: 'Completion %',
      render: (v: VendorPerformanceItem) => (
        <span className="font-mono text-slate-300">
          {(v.completion_rate * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Audit Status',
      render: (v: VendorPerformanceItem) => {
        if (v.sla_breach_rate >= 0.25) {
          return <StatusBadge status="failed" />;
        }
        if (v.sla_breach_rate > 0.1) {
          return <StatusBadge status="warning" />;
        }
        return <StatusBadge status="processed" />;
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-blue-400" />
            Vendor Performance Analytics
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Multidimensional evaluation of supplier procurement volume, cycle times, spend, and SLA compliance.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Suppliers"
          value={totalVendors}
          subtext={`Across ${totalCases.toLocaleString()} procurement orders`}
          icon={<Building2 className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Total Vendor Spend"
          value={`$${(totalSpend / 1000000).toFixed(2)}M`}
          subtext={`Top vendor: ${topVendorBySpend ? topVendorBySpend.vendor_id : 'N/A'} ($${topVendorBySpend ? (topVendorBySpend.total_spend_usd / 1000).toFixed(0) : 0}k)`}
          icon={<DollarSign className="w-4 h-4 text-emerald-400" />}
        />
        <MetricCard
          title="Avg Supplier Cycle Time"
          value={`${avgCycleTime}h`}
          subtext="From PR creation to payment receipt"
          icon={<Clock className="w-4 h-4 text-indigo-400" />}
        />
        <MetricCard
          title="SLA Breach Rate"
          value={`${overallBreachRate}%`}
          subtext={`${totalBreaches.toLocaleString()} orders exceeded 720h SLA`}
          icon={<ShieldAlert className={`w-4 h-4 ${overallBreachRate > 15 ? 'text-rose-400' : 'text-amber-400'}`} />}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top 10 by Spend */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                Top 10 Suppliers by Total Spend
              </h2>
              <p className="text-xs text-slate-400">Identifies highest capital exposure suppliers</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top10Spend} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                <XAxis dataKey="vendor_id" stroke="#64748B" fontSize={10} tickLine={false} interval={0} angle={-30} textAnchor="end" />
                <YAxis
                  stroke="#64748B"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '0.5rem', fontSize: '11px' }}
                  formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Total Spend']}
                />
                <Bar dataKey="total_spend_usd" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Highest Cycle Times */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                Suppliers with Longest Cycle Times
              </h2>
              <p className="text-xs text-slate-400">Suppliers causing operational procurement lag (min 3 cases)</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top10Cycle} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                <XAxis dataKey="vendor_id" stroke="#64748B" fontSize={10} tickLine={false} interval={0} angle={-30} textAnchor="end" />
                <YAxis stroke="#64748B" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(val) => `${val}h`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '0.5rem', fontSize: '11px' }}
                  formatter={(value: any) => [`${Number(value).toFixed(1)} hours`, 'Avg Cycle Time']}
                />
                <ReferenceLine y={720} stroke="#EF4444" strokeDasharray="4 4" label={{ value: 'SLA (720h)', fill: '#EF4444', fontSize: 10, position: 'top' }} />
                <Bar dataKey="avg_cycle_time_hours" fill="#6366F1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Vendor Table Section */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-400" />
              Supplier Audit Ledger
            </h2>
            <p className="text-xs text-slate-400">Complete performance and SLA compliance breakdown per vendor</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search vendor ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-surface border border-surface-border text-xs text-slate-100 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-blue-500 w-44"
              />
            </div>

            {/* Sort Dropdown */}
            <select
              value={selectedSort}
              onChange={(e) => setSelectedSort(e.target.value as any)}
              className="bg-surface border border-surface-border text-xs text-slate-100 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
            >
              <option value="spend">Sort by Spend</option>
              <option value="cases">Sort by Cases</option>
              <option value="cycle_time">Sort by Cycle Time</option>
              <option value="sla">Sort by SLA Breach Rate</option>
            </select>
          </div>
        </div>

        <DataTable
          columns={columns}
          data={sortedVendors}
          pageSize={10}
        />
      </div>
    </div>
  );
};
