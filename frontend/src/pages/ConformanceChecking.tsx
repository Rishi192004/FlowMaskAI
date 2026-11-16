import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  CheckCircle2,
  FileSearch,
  Filter,
  Save,
  Settings,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react';
import { conformanceApi } from '../../api/conformance';
import { DataTable } from '../../components/common/DataTable';
import { EmptyState, ErrorState, LoadingState } from '../../components/common/FeedbackStates';
import { MetricCard } from '../../components/common/MetricCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { useFilters } from '../../context/FilterContext';
import {
  CaseDeviationItem,
  CaseDeviationsListResponse,
  ConformanceOverviewResponse,
  ConformanceRulesConfig,
  DeviationSummaryItem,
} from '../../types/api';

export const ConformanceChecking: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate } = useFilters();
  const [overview, setOverview] = useState<ConformanceOverviewResponse | null>(null);
  const [casesData, setCasesData] = useState<CaseDeviationsListResponse | null>(null);
  const [filterDeviantOnly, setFilterDeviantOnly] = useState<boolean>(true);
  const [selectedCase, setSelectedCase] = useState<CaseDeviationItem | null>(null);
  const [showRulesModal, setShowRulesModal] = useState<boolean>(false);
  const [rulesConfig, setRulesConfig] = useState<ConformanceRulesConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConformance = async () => {
    if (!selectedDatasetId) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const [ovRes, casesRes, rulesRes] = await Promise.all([
        conformanceApi.getOverview({
          dataset_id: selectedDatasetId,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        }),
        conformanceApi.getCases({
          dataset_id: selectedDatasetId,
          filter_deviant_only: filterDeviantOnly,
          page: 1,
          page_size: 50,
        }),
        conformanceApi.getRules(selectedDatasetId),
      ]);

      setOverview(ovRes);
      setCasesData(casesRes);
      setRulesConfig(rulesRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to execute conformance checking.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConformance();
  }, [selectedDatasetId, startDate, endDate, filterDeviantOnly]);

  const handleUpdateRules = async () => {
    if (!selectedDatasetId || !rulesConfig) return;
    try {
      setIsLoading(true);
      await conformanceApi.updateRules(selectedDatasetId, rulesConfig);
      setShowRulesModal(false);
      await fetchConformance();
    } catch (err: any) {
      setError(err?.message || 'Failed to update rules.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!selectedDataset) {
    return <EmptyState title="No Dataset Selected" description="Select an event log to check process conformance." />;
  }

  if (isLoading) {
    return <LoadingState message="Replaying event tokens and checking compliance against reference rules..." />;
  }

  if (error || !overview || !casesData) {
    return <ErrorState message={error || 'Failed to check conformance.'} onRetry={fetchConformance} />;
  }

  const caseColumns = [
    {
      key: 'case_id',
      header: 'Case ID',
      render: (c: CaseDeviationItem) => (
        <span className="font-mono text-xs font-semibold text-slate-200">{c.case_id}</span>
      ),
      width: '130px',
    },
    {
      key: 'is_conformant',
      header: 'Status',
      render: (c: CaseDeviationItem) => (
        <StatusBadge status={c.is_conformant ? 'Conformant' : 'Deviant'} size="sm" />
      ),
      width: '110px',
    },
    {
      key: 'fitness_score',
      header: 'Fitness Score',
      render: (c: CaseDeviationItem) => (
        <span className={`font-mono text-xs font-semibold ${
          c.fitness_score >= 0.9 ? 'text-emerald-400' : c.fitness_score >= 0.7 ? 'text-amber-400' : 'text-rose-400'
        }`}>
          {(c.fitness_score * 100).toFixed(1)}%
        </span>
      ),
      width: '110px',
    },
    {
      key: 'deviations',
      header: 'Root Causes & Violations',
      render: (c: CaseDeviationItem) => (
        <div className="space-y-1">
          {c.deviations.length === 0 ? (
            <span className="text-xs text-slate-500 font-mono">100% Matches Expected Flow</span>
          ) : (
            c.deviations.map((d, i) => (
              <div key={i} className="text-[11px] flex items-center gap-1.5">
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono border ${
                  d.severity === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}>
                  {d.deviation_type}
                </span>
                <span className="text-slate-400 truncate max-w-md">{d.description}</span>
              </div>
            ))
          )}
        </div>
      ),
    },
    {
      key: 'duration_hours',
      header: 'Cycle Time',
      render: (c: CaseDeviationItem) => (
        <span className="font-mono text-slate-400 text-xs">{c.duration_hours}h</span>
      ),
      width: '90px',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100">Conformance Checking & Audit</h2>
          <p className="text-xs text-slate-400 mt-1">
            Detect process violations, skipped approvals, 3-way match failures, and out-of-order execution against reference rules.
          </p>
        </div>

        <button
          onClick={() => setShowRulesModal(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-surface-card hover:bg-surface-hover border border-surface-border text-slate-200 text-xs font-semibold rounded-lg transition-colors"
        >
          <Settings className="w-3.5 h-3.5 text-blue-400" />
          <span>Configure Business Rules</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Conformance Rate"
          value={`${overview.conformance_percentage}%`}
          subtext={`${overview.conformant_cases} of ${overview.total_cases} cases conformant`}
          icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
          badge={{
            text: overview.conformance_percentage >= 80 ? 'High' : 'Low',
            variant: overview.conformance_percentage >= 80 ? 'success' : 'danger',
          }}
        />
        <MetricCard
          title="Average Token Fitness"
          value={`${(overview.average_fitness_score * 100).toFixed(1)}%`}
          subtext="PM4Py token-based replay fitness"
          icon={<CheckCircle2 className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Deviant Cases"
          value={overview.deviant_cases}
          subtext={`${(100 - overview.conformance_percentage).toFixed(1)}% exhibit rule violations`}
          icon={<ShieldAlert className="w-4 h-4 text-rose-400" />}
          badge={{ text: 'Requires Audit', variant: 'danger' }}
        />
        <MetricCard
          title="Distinct Violations"
          value={overview.deviation_breakdown.length}
          subtext="Categorized compliance risks"
          icon={<AlertOctagon className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Violation Frequency Breakdown Cards */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-slate-100">Deviation Frequency Breakdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {overview.deviation_breakdown.map(d => (
            <div key={d.deviation_type} className="p-3 bg-surface border border-surface-border rounded-lg space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-slate-200">{d.deviation_type}</span>
                <StatusBadge status={d.severity} size="sm" />
              </div>
              <p className="text-[11px] text-slate-400">{d.description}</p>
              <div className="text-xs font-mono text-blue-400 font-semibold pt-1">
                {d.affected_cases} cases ({d.percentage_of_cases}%)
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Case-Level Audit Table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <FileSearch className="w-4 h-4 text-slate-400" />
            <span>Case-Level Deviation Drill-Down</span>
          </h3>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterDeviantOnly(true)}
              className={`px-2.5 py-1 text-xs rounded-lg font-medium border transition-colors ${
                filterDeviantOnly
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                  : 'bg-surface text-slate-400 border-surface-border hover:bg-surface-hover'
              }`}
            >
              Deviant Cases Only ({overview.deviant_cases})
            </button>
            <button
              onClick={() => setFilterDeviantOnly(false)}
              className={`px-2.5 py-1 text-xs rounded-lg font-medium border transition-colors ${
                !filterDeviantOnly
                  ? 'bg-blue-600 text-white border-blue-500'
                  : 'bg-surface text-slate-400 border-surface-border hover:bg-surface-hover'
              }`}
            >
              All Cases ({overview.total_cases})
            </button>
          </div>
        </div>

        <DataTable
          columns={caseColumns}
          data={casesData.cases}
          searchKey="case_id"
          searchPlaceholder="Search by Case ID..."
          onRowClick={c => setSelectedCase(c)}
        />
      </div>

      {/* Selected Case Root-Cause Modal / Inspection */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-surface-border rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span>Case Root-Cause Audit:</span>
                  <span className="font-mono text-blue-400">{selectedCase.case_id}</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Fitness: {(selectedCase.fitness_score * 100).toFixed(1)}% • Duration: {selectedCase.duration_hours}h • Events: {selectedCase.total_events}
                </p>
              </div>
              <button onClick={() => setSelectedCase(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {selectedCase.deviations.length === 0 ? (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300">
                  ✓ This case adheres 100% to the reference process sequence without any detected violations.
                </div>
              ) : (
                selectedCase.deviations.map((dev, idx) => (
                  <div key={idx} className="p-4 bg-surface border border-surface-border rounded-lg space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-rose-400 text-xs">{dev.deviation_type}</span>
                      <StatusBadge status={dev.severity} size="sm" />
                    </div>
                    <p className="text-slate-200">{dev.description}</p>
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono pt-1 text-slate-400 border-t border-surface-border/50">
                      <div>
                        <span className="text-slate-500 block">Culprit Event:</span>
                        <strong className="text-slate-300">{dev.culprit_activity}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Observed Transition:</span>
                        <span className="text-amber-400">{dev.actual}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedCase(null)}
                className="px-4 py-2 bg-surface hover:bg-surface-hover border border-surface-border text-slate-300 text-xs font-medium rounded-lg"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rules Config Modal */}
      {showRulesModal && rulesConfig && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-surface-border rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Settings className="w-4 h-4 text-blue-400" />
                <span>Configure Business Rules & Policies</span>
              </h3>
              <button onClick={() => setShowRulesModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={rulesConfig.require_manager_approval}
                  onChange={e => setRulesConfig({ ...rulesConfig, require_manager_approval: e.target.checked })}
                  className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-semibold text-slate-200">Mandate Manager Approval</span>
                  <p className="text-[11px] text-slate-400">Flag cases where Purchase Order is created without prior approval.</p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={rulesConfig.prohibit_early_invoice_verification}
                  onChange={e => setRulesConfig({ ...rulesConfig, prohibit_early_invoice_verification: e.target.checked })}
                  className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-semibold text-slate-200">Enforce 3-Way Match (Goods Receipt Before Invoice Verification)</span>
                  <p className="text-[11px] text-slate-400">Flag cases where Invoice is verified prior to physical Goods Receipt.</p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={rulesConfig.allow_repeated_approval}
                  onChange={e => setRulesConfig({ ...rulesConfig, allow_repeated_approval: e.target.checked })}
                  className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-semibold text-slate-200">Allow Repeated Approvals (Rework Tolerance)</span>
                  <p className="text-[11px] text-slate-400">If unchecked, multiple approval cycles in a single case trigger rework violations.</p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-surface border border-surface-border rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={rulesConfig.require_payment_completion}
                  onChange={e => setRulesConfig({ ...rulesConfig, require_payment_completion: e.target.checked })}
                  className="mt-0.5 rounded border-slate-700 bg-surface-card text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-semibold text-slate-200">Require Payment Completed Milestone</span>
                  <p className="text-[11px] text-slate-400">Flag unfinished workflows that stall before payment.</p>
                </div>
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-surface-border">
              <button
                onClick={() => setShowRulesModal(false)}
                className="px-4 py-2 bg-surface hover:bg-surface-hover border border-surface-border text-slate-300 text-xs font-medium rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateRules}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save & Re-evaluate</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
