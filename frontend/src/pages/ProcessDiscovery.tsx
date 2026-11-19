import React, { useEffect, useState } from 'react';
import { Activity, ArrowRight, Layers, Sparkles, X } from 'lucide-react';
import { processApi } from '../api/process';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { ProcessMapCanvas } from '../components/process/ProcessMapCanvas';
import { useFilters } from '../context/FilterContext';
import { ProcessDiscoveryResponse, ProcessMapNode, ProcessMapResponse } from '../types/api';

export const ProcessDiscovery: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate, selectedDepartment, selectedVendor } = useFilters();
  const [mapData, setMapData] = useState<ProcessMapResponse | null>(null);
  const [discoveryData, setDiscoveryData] = useState<ProcessDiscoveryResponse | null>(null);
  const [algorithm, setAlgorithm] = useState<'dfg' | 'inductive'>('dfg');
  const [selectedNode, setSelectedNode] = useState<ProcessMapNode | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProcessData = async () => {
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
        department: selectedDepartment || undefined,
        vendor_id: selectedVendor || undefined,
      };

      const [mapRes, discRes] = await Promise.all([
        processApi.getMap(params),
        processApi.getDiscovery(params),
      ]);

      setMapData(mapRes);
      setDiscoveryData(discRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate process discovery model.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProcessData();
  }, [selectedDatasetId, startDate, endDate, selectedDepartment, selectedVendor]);

  if (!selectedDataset) {
    return <EmptyState title="No Dataset Selected" description="Select a dataset to discover its business workflow graph." />;
  }

  if (isLoading) {
    return <LoadingState message="Discovering process model and computing Directly-Follows Graph..." />;
  }

  if (error || !mapData) {
    return <ErrorState message={error || 'Failed to discover process graph.'} onRetry={fetchProcessData} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100">Process Discovery & Mapping</h2>
          <p className="text-xs text-slate-400 mt-1">
            Interactive process graph reconstructed from raw event timestamps using PM4Py algorithms.
          </p>
        </div>

        {/* Algorithm Switcher */}
        <div className="flex items-center gap-2 bg-surface-card border border-surface-border p-1 rounded-xl">
          <button
            onClick={() => setAlgorithm('dfg')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              algorithm === 'dfg' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Directly-Follows Graph (DFG)
          </button>
          <button
            onClick={() => setAlgorithm('inductive')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              algorithm === 'inductive' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Inductive Miner (Petri Net)
          </button>
        </div>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard title="Total Activities" value={mapData.nodes.length} subtext="Unique process steps" />
        <MetricCard title="Direct Transitions" value={mapData.edges.length} subtext="Directly-follows edges" />
        <MetricCard
          title="Start Activities"
          value={Object.keys(mapData.start_activities).length}
          subtext={Object.keys(mapData.start_activities).join(', ') || 'None'}
          badge={{ text: 'Entry Point', variant: 'info' }}
        />
        <MetricCard
          title="End Activities"
          value={Object.keys(mapData.end_activities).length}
          subtext={Object.keys(mapData.end_activities).join(', ') || 'None'}
          badge={{ text: 'Completion Point', variant: 'success' }}
        />
      </div>

      {/* Process Graph Canvas */}
      {algorithm === 'dfg' ? (
        <div className="space-y-4">
          <ProcessMapCanvas
            nodes={mapData.nodes}
            edges={mapData.edges}
            onSelectNode={n => setSelectedNode(n)}
          />

          {/* Node Detail Drawer / Inspection */}
          {selectedNode && (
            <div className="p-4 bg-surface-card border border-surface-border rounded-xl flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-100">{selectedNode.label}</span>
                  {selectedNode.is_start && <StatusBadge status="Process Start" size="sm" />}
                  {selectedNode.is_end && <StatusBadge status="Process End" size="sm" />}
                  {selectedNode.is_bottleneck && <StatusBadge status="Bottleneck" size="sm" />}
                </div>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  Volume: {selectedNode.frequency.toLocaleString()} executions • Average Queue Delay: {selectedNode.avg_duration_hours}h
                </p>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 text-slate-500 hover:text-slate-300 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Inductive Miner Petri Net Inspector */
        <div className="bg-surface-card border border-surface-border rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-100">PM4Py Inductive Miner Petri Net</h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Places: {discoveryData?.places.length || 0} • Transitions: {discoveryData?.transitions.length || 0} • Arcs: {discoveryData?.arcs.length || 0}
              </p>
            </div>
            <StatusBadge status="Inductive Sound Net" size="sm" />
          </div>

          {discoveryData?.process_tree_repr && (
            <div className="p-3 bg-surface border border-surface-border rounded-lg text-xs font-mono text-emerald-400">
              <span className="text-slate-500 block mb-1">Discovered Process Tree:</span>
              {discoveryData.process_tree_repr}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 bg-surface border border-surface-border rounded-lg max-h-60 overflow-y-auto space-y-1">
              <span className="text-slate-400 font-semibold block mb-2">Petri Net Transitions:</span>
              {discoveryData?.transitions.map(t => (
                <div key={t.id} className="text-slate-300">
                  <span className="text-blue-400">{t.id}</span>: {t.label || 'tau (silent)'}
                </div>
              ))}
            </div>

            <div className="p-4 bg-surface border border-surface-border rounded-lg max-h-60 overflow-y-auto space-y-1">
              <span className="text-slate-400 font-semibold block mb-2">Petri Net Arcs:</span>
              {discoveryData?.arcs.map((a, i) => (
                <div key={i} className="text-slate-300">
                  {a.source} → {a.target}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
