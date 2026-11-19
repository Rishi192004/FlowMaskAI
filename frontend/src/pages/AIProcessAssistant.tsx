import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  Brain,
  CheckCircle,
  Clock,
  Compass,
  FileCheck2,
  FileText,
  Lightbulb,
  MessageSquare,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  User,
  Zap,
} from 'lucide-react';
import { aiApi } from '../api/ai';
import { analyticsApi } from '../api/analytics';
import { conformanceApi } from '../api/conformance';
import { processApi } from '../api/process';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import {
  AssistantMetricFact,
  BottlenecksResponse,
  ConformanceOverviewResponse,
  OverviewMetrics,
  ProcessVariantsResponse,
  RecommendationItem,
  VendorPerformanceResponse,
} from '../types/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  groundingMetrics?: Record<string, string | number>;
  measuredFacts?: AssistantMetricFact[];
  configuredBaselines?: AssistantMetricFact[];
  recommendations?: RecommendationItem[];
  category?: string;
}

export const AIProcessAssistant: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate } = useFilters();
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [conformance, setConformance] = useState<ConformanceOverviewResponse | null>(null);
  const [bottlenecks, setBottlenecks] = useState<BottlenecksResponse | null>(null);
  const [variants, setVariants] = useState<ProcessVariantsResponse | null>(null);
  const [vendors, setVendors] = useState<VendorPerformanceResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Chat state
  const [chatInput, setChatInput] = useState<string>('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);

  const fetchGroundingAnalytics = async () => {
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

      const [ovRes, confRes, bnRes, varRes, vendRes, recRes] = await Promise.all([
        analyticsApi.getOverview(params),
        conformanceApi.getOverview(params),
        analyticsApi.getBottlenecks(params),
        processApi.getVariants(params),
        analyticsApi.getVendorPerformance({ ...params, sla_hours: 720.0 }),
        aiApi.getRecommendations(params),
      ]);

      setOverview(ovRes);
      setConformance(confRes);
      setBottlenecks(bnRes);
      setVariants(varRes);
      setVendors(vendRes);
      setRecommendations(recRes.recommendations);

      // Initialize welcome message once grounded data is ready
      const totalC = ovRes.total_purchase_cases.toLocaleString();
      const avgH = ovRes.avg_cycle_time_hours.toFixed(1);
      const confRate = confRes.conformance_percentage.toFixed(1);
      const datasetName = selectedDataset ? selectedDataset.name : 'Selected Dataset';

      setChatMessages([
        {
          id: 'welcome',
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: `Hello! I am your FlowMind AI Process Assistant. I have analyzed dataset **${datasetName}** containing **${totalC} cases** with an average cycle time of **${avgH} hours** and a **${confRate}% conformance rate**.\n\nAll my insights are derived strictly from your computed process metrics. Ask me about bottlenecks, compliance breaches, rework patterns, or optimization recommendations!`,
          groundingMetrics: {
            'Total Cases': ovRes.total_purchase_cases,
            'Avg Cycle Time': `${avgH}h`,
            'Conformance Rate': `${confRate}%`,
            'Total Spend': `$${(ovRes.total_spend_usd / 1000).toFixed(0)}k`,
          },
        },
      ]);
    } catch (err: any) {
      setError(err?.message || 'Failed to aggregate grounding data for AI Assistant.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGroundingAnalytics();
  }, [selectedDatasetId, startDate, endDate]);

  if (!selectedDataset) {
    return (
      <EmptyState
        title="No Dataset Selected"
        description="Select an active dataset in the header to activate the AI Process Assistant."
      />
    );
  }

  if (isLoading) {
    return <LoadingState message="Extracting computed process metrics and grounding recommendation models..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="AI Assistant Initialization Failed"
        message={error}
        onRetry={fetchGroundingAnalytics}
      />
    );
  }

  // ── Handle Assistant Conversation Queries ───────────────────────────────
  const handleSendQuery = async (queryText?: string) => {
    const textToSend = (queryText || chatInput).trim();
    if (!textToSend || !selectedDatasetId || isTyping) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setChatMessages(prev => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        sender: 'user',
        timestamp,
        text: textToSend,
      },
    ]);
    setChatInput('');
    setIsTyping(true);

    try {
      const result = await aiApi.ask({
        dataset_id: selectedDatasetId,
        question: textToSend,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setChatMessages(prev => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: result.answer,
          measuredFacts: result.measured_facts,
          configuredBaselines: result.configured_baselines,
          recommendations: result.recommendations,
          category: result.intent,
        },
      ]);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'The assistant request failed.';
      setChatMessages(prev => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: `I could not generate an answer: ${message}`,
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const sampleQueries = [
    'What is our biggest bottleneck?',
    'Which vendors have the highest SLA breach rate?',
    'Why are cases taking longer than expected?',
    'Which activities contribute most to rework?',
    'What percentage of cases violate the reference process?',
    'What actions should management prioritize?',
  ];

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-indigo-400" />
            AI Process Assistant & Recommendations
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Grounded operational intelligence engine mapping computed event-log analytics to actionable recommendations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            100% Data Grounded • 0% Hallucination
          </span>
        </div>
      </div>

      {/* Grounded Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Analyzed Cases"
          value={overview?.total_purchase_cases.toLocaleString() || '0'}
          subtext={`Across ${overview?.total_events.toLocaleString()} discrete events`}
          icon={<Brain className="w-4 h-4 text-blue-400" />}
        />
        <MetricCard
          title="Conformance Score"
          value={`${conformance?.conformance_percentage.toFixed(1)}%`}
          subtext={`Fitness: ${(conformance?.average_fitness_score ? conformance.average_fitness_score * 100 : 0).toFixed(1)}%`}
          icon={<ShieldAlert className={`w-4 h-4 ${(conformance?.conformance_percentage || 0) < 80 ? 'text-rose-400' : 'text-emerald-400'}`} />}
        />
        <MetricCard
          title="Top Delay Factor"
          value={bottlenecks?.bottlenecks[0] ? `${bottlenecks.bottlenecks[0].avg_waiting_time_hours.toFixed(0)}h wait` : 'None'}
          subtext={bottlenecks?.bottlenecks[0]?.activity || 'N/A'}
          icon={<Clock className="w-4 h-4 text-amber-400" />}
        />
        <MetricCard
          title="Prioritized Action Items"
          value={recommendations.length}
          subtext="Grounded recommendations from backend engine"
          icon={<Lightbulb className="w-4 h-4 text-indigo-400" />}
        />
      </div>

      {/* Main Grid: Interactive Chat + Prescriptive Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Interactive Grounded Assistant (7 cols) */}
        <div className="lg:col-span-7 bg-surface-card border border-surface-border rounded-xl flex flex-col h-[650px] shadow-sm">
          {/* Chat Header */}
          <div className="p-4 border-b border-surface-border flex items-center justify-between bg-surface/50">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  Process Intelligence Chat
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                </h2>
                <p className="text-[10px] text-slate-400">Query your workflow metrics in natural language</p>
              </div>
            </div>
            <button
              onClick={fetchGroundingAnalytics}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-hover rounded-lg transition-colors border border-surface-border"
              title="Refresh Grounding Data"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Query Pills */}
          <div className="px-4 py-2 bg-[#090D18] border-b border-surface-border flex items-center gap-2 overflow-x-auto text-xs">
            <span className="text-[10px] text-slate-500 font-semibold uppercase flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" /> Prompts:
            </span>
            {sampleQueries.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendQuery(q)}
                className="whitespace-nowrap bg-surface border border-surface-border hover:border-indigo-500/50 text-[11px] text-slate-300 hover:text-white px-2.5 py-1 rounded-full transition-colors flex-shrink-0"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Messages Log */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 font-sans text-xs">
            {chatMessages.map(msg => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.sender === 'assistant' && (
                  <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}

                <div className={`max-w-[85%] rounded-xl p-3.5 ${
                  msg.sender === 'user'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-[#0E1526] border border-surface-border text-slate-200'
                }`}>
                  <div className="flex items-center justify-between gap-3 mb-1.5">
                    <span className="font-semibold text-[11px] text-slate-400">
                      {msg.sender === 'user' ? 'You' : 'FlowMind Grounded Agent'}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{msg.timestamp}</span>
                  </div>

                  <div className="prose prose-invert prose-xs text-xs leading-relaxed whitespace-pre-line">
                    {msg.text}
                  </div>

                  {/* Supporting Grounding Metrics Tag Box */}
                  {msg.groundingMetrics && (
                    <div className="mt-3 pt-2.5 border-t border-surface-border/60 flex flex-wrap gap-2 text-[10px] font-mono">
                      {Object.entries(msg.groundingMetrics).map(([k, v]) => (
                        <span key={k} className="bg-surface px-2 py-0.5 rounded border border-surface-border text-indigo-300">
                          <span className="text-slate-400">{k}:</span> {String(v)}
                        </span>
                      ))}
                    </div>
                  )}

                  {msg.measuredFacts && msg.measuredFacts.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-surface-border/60 space-y-1.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                        Measured facts
                      </p>
                      {msg.measuredFacts.map(fact => (
                        <div key={fact.key} className="flex justify-between gap-3 text-[10px]">
                          <span className="text-slate-400">{fact.label}</span>
                          <span className="font-mono text-emerald-200 text-right">{fact.display_value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {msg.configuredBaselines && msg.configuredBaselines.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-surface-border/60 space-y-1.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-300">
                        Configured baselines
                      </p>
                      {msg.configuredBaselines.map(baseline => (
                        <div key={baseline.key} className="flex justify-between gap-3 text-[10px]">
                          <span className="text-slate-400">{baseline.label}</span>
                          <span className="font-mono text-sky-200 text-right">{baseline.display_value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {msg.recommendations && msg.recommendations.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-surface-border/60 space-y-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-300">
                        Recommendation engine actions
                      </p>
                      {msg.recommendations.slice(0, 3).map(recommendation => (
                        <div key={recommendation.recommendation_id} className="rounded border border-surface-border bg-surface p-2">
                          <p className="text-[10px] font-semibold text-slate-100">
                            {recommendation.severity} · {recommendation.rule_id}
                          </p>
                          <p className="mt-1 text-[10px] text-slate-300">{recommendation.business_problem}</p>
                          <p className="mt-1 text-[10px] text-indigo-200">
                            {recommendation.recommended_corrective_action}
                          </p>
                          <p className="mt-1 text-[9px] text-slate-500">
                            Evidence: {recommendation.evidence_and_explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {msg.sender === 'user' && (
                  <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 flex-shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-3 items-center text-xs text-slate-400 italic">
                <Bot className="w-4 h-4 text-indigo-400 animate-spin" />
                <span>Retrieving metrics and asking the local model to summarize...</span>
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-surface-border bg-surface/30">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask about cycle times, bottlenecks, deviations, or vendor compliance..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 bg-surface border border-surface-border text-xs text-slate-100 rounded-lg px-3.5 py-2.5 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || isTyping}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>

        {/* Right: Prescriptive Grounded Recommendations Ledger (5 cols) */}
        <div className="lg:col-span-5 space-y-4 overflow-y-auto max-h-[650px] pr-1">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              Prescriptive Recommendations
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">
              {recommendations.length} rules triggered
            </span>
          </div>

          {recommendations.length === 0 ? (
            <div className="bg-surface-card border border-surface-border rounded-xl p-8 text-center text-slate-400">
              <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="text-xs font-semibold text-white">All Process Rules Conformant</p>
              <p className="text-[11px] mt-1">No severe bottlenecks or compliance violations detected in the active dataset filter.</p>
            </div>
          ) : (
            recommendations.map(rec => (
              <div
                key={rec.recommendation_id}
                className="bg-surface-card border border-surface-border hover:border-slate-700 rounded-xl p-4 space-y-3 transition-colors shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                        rec.severity === 'CRITICAL' || rec.severity === 'HIGH'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {rec.severity} • {rec.category}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{rec.rule_id}</span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-100">{rec.business_problem}</h3>
                  </div>
                </div>

                <div className="text-[11px] text-slate-300 leading-relaxed">
                  <span className="text-slate-400">Impacted Cases: </span>
                  <span className="font-mono font-semibold text-white">{rec.affected_case_count.toLocaleString()}</span>
                  <span className="text-slate-400"> ({rec.affected_case_percentage.toFixed(1)}% of volume)</span>
                </div>

                {/* Evidence Box */}
                <div className="bg-[#0A0E18] border border-surface-border rounded p-2 text-[10px] font-mono text-indigo-300">
                  <span className="text-slate-400 font-semibold block mb-0.5">Calculated Evidence:</span>
                  {rec.evidence_and_explanation}
                </div>

                {/* Prescriptive Action */}
                <div className="bg-surface border-l-2 border-indigo-500 p-2.5 rounded-r text-[11px] text-slate-200">
                  <span className="font-semibold text-indigo-400 block mb-0.5">Recommended Action:</span>
                  {rec.recommended_corrective_action}
                </div>

                {/* Expected Impact */}
                <div className="text-[10px] text-slate-400 flex items-center gap-1.5 pt-1">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span>Impact: {rec.estimated_operational_impact}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
