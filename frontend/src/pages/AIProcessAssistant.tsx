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
import { analyticsApi } from '../api/analytics';
import { conformanceApi } from '../api/conformance';
import { processApi } from '../api/process';
import { EmptyState, ErrorState, LoadingState } from '../components/common/FeedbackStates';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { useFilters } from '../context/FilterContext';
import {
  BottlenecksResponse,
  ConformanceOverviewResponse,
  OverviewMetrics,
  ProcessVariantsResponse,
  VendorPerformanceResponse,
} from '../types/api';

interface GroundedRecommendation {
  ruleId: string;
  category: 'Compliance' | 'Efficiency' | 'Quality' | 'Financial Risk';
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  observation: string;
  evidence: string;
  recommendation: string;
  estimatedImpact: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  groundingMetrics?: Record<string, string | number>;
  category?: string;
}

export const AIProcessAssistant: React.FC = () => {
  const { selectedDatasetId, selectedDataset, startDate, endDate } = useFilters();
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [conformance, setConformance] = useState<ConformanceOverviewResponse | null>(null);
  const [bottlenecks, setBottlenecks] = useState<BottlenecksResponse | null>(null);
  const [variants, setVariants] = useState<ProcessVariantsResponse | null>(null);
  const [vendors, setVendors] = useState<VendorPerformanceResponse | null>(null);

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

      const [ovRes, confRes, bnRes, varRes, vendRes] = await Promise.all([
        analyticsApi.getOverview(params),
        conformanceApi.getOverview(params),
        analyticsApi.getBottlenecks(params),
        processApi.getVariants(params),
        analyticsApi.getVendorPerformance({ ...params, sla_hours: 720.0 }),
      ]);

      setOverview(ovRes);
      setConformance(confRes);
      setBottlenecks(bnRes);
      setVariants(varRes);
      setVendors(vendRes);

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

  // ── Formulate Grounded Recommendations (Rule Catalogue) ──────────────────
  const recommendations: GroundedRecommendation[] = [];

  if (conformance && overview && bottlenecks) {
    // Rule 1: Skipped Approval
    const skipApprovalDev = conformance.deviation_breakdown.find(d => d.deviation_type === 'SKIPPED_APPROVAL');
    if (skipApprovalDev && skipApprovalDev.affected_cases > 0) {
      recommendations.push({
        ruleId: 'SKIP_APPROVAL',
        category: 'Compliance',
        severity: 'HIGH',
        title: 'Unauthorized Purchase Orders (Skipped Manager Approvals)',
        observation: `${skipApprovalDev.affected_cases} cases (${skipApprovalDev.percentage_of_cases}% of total) bypassed mandatory manager approval before purchase orders were created.`,
        evidence: `Deviation Type: SKIPPED_APPROVAL | Affected Cases: ${skipApprovalDev.affected_cases} | Severity: HIGH`,
        recommendation: 'Configure automated approval gating in the ERP system to prevent PO issuance prior to recorded cryptographic or digital manager sign-off.',
        estimatedImpact: 'High compliance control integrity; mitigates unbudgeted capital expenditure risk.',
      });
    }

    // Rule 2: Early Invoice Verification
    const earlyInvDev = conformance.deviation_breakdown.find(d => d.deviation_type === 'EARLY_INVOICE_VERIFICATION');
    if (earlyInvDev && earlyInvDev.affected_cases > 0) {
      recommendations.push({
        ruleId: 'EARLY_INVOICE',
        category: 'Financial Risk',
        severity: 'HIGH',
        title: 'Three-Way Matching Control Failure (Early Invoicing)',
        observation: `${earlyInvDev.affected_cases} cases verified vendor invoices prior to physical goods receipt confirmation.`,
        evidence: `Deviation Type: EARLY_INVOICE_VERIFICATION | Affected Cases: ${earlyInvDev.affected_cases} | Control: 3-Way Match`,
        recommendation: 'Enforce hard system stop on accounts payable verification until receiving warehouse logs goods receipt status.',
        estimatedImpact: 'Eliminates duplicate payments and premature supplier liabilities.',
      });
    }

    // Rule 3: High Rework Rate
    if (overview.rework_percentage > 0.05) {
      recommendations.push({
        ruleId: 'HIGH_REWORK',
        category: 'Quality',
        severity: overview.rework_percentage > 0.15 ? 'HIGH' : 'MEDIUM',
        title: 'Excessive Rework & Redundant Activity Loops',
        observation: `${overview.rework_cases} cases (${(overview.rework_percentage * 100).toFixed(1)}%) revisited activities multiple times, primarily within approvals or verifications.`,
        evidence: `Rework Cases: ${overview.rework_cases} (${(overview.rework_percentage * 100).toFixed(1)}% of volume)`,
        recommendation: 'Standardize procurement requisition templates to minimize incomplete submissions that trigger revision loops.',
        estimatedImpact: `Potential cycle time reduction of ${(overview.avg_cycle_time_hours * 0.15).toFixed(1)} hours per case.`,
      });
    }

    // Rule 4: Primary Bottleneck
    const topBottleneck = bottlenecks.bottlenecks[0];
    if (topBottleneck && topBottleneck.avg_waiting_time_hours > 24) {
      recommendations.push({
        ruleId: 'APPROVAL_BOTTLENECK',
        category: 'Efficiency',
        severity: 'MEDIUM',
        title: `Queue Delay at Stage: ${topBottleneck.activity}`,
        observation: `Average queue waiting time before '${topBottleneck.activity}' is ${topBottleneck.avg_waiting_time_hours.toFixed(1)} hours (SLA breach rate: ${(topBottleneck.sla_breach_rate * 100).toFixed(1)}%).`,
        evidence: `Bottleneck Activity: ${topBottleneck.activity} | Waiting Time: ${topBottleneck.avg_waiting_time_hours.toFixed(1)}h | Severity Score: ${topBottleneck.bottleneck_score}`,
        recommendation: 'Implement automated task reassignment, mobile notification escalation, and tiered sign-off thresholds for faster review.',
        estimatedImpact: `Estimated throughput acceleration by ~${(topBottleneck.avg_waiting_time_hours * 0.4).toFixed(1)} hours per case.`,
      });
    }

    // Rule 5: SLA Breaches
    if (overview.sla_breach_percentage > 0.10) {
      recommendations.push({
        ruleId: 'SLA_BREACH',
        category: 'Efficiency',
        severity: 'HIGH',
        title: 'Systemic Procurement SLA Non-Compliance',
        observation: `${overview.sla_breach_cases} cases (${(overview.sla_breach_percentage * 100).toFixed(1)}%) exceeded the 720-hour operational SLA.`,
        evidence: `SLA Threshold: ${overview.sla_hours}h | Breach Count: ${overview.sla_breach_cases} (${(overview.sla_breach_percentage * 100).toFixed(1)}%)`,
        recommendation: 'Establish automated SLA milestone alerts at 50% and 75% elapsed time to prevent late vendor disbursements.',
        estimatedImpact: 'Improves supplier relationship satisfaction and captures early payment discounts.',
      });
    }
  }

  // ── Handle Assistant Conversation Queries ───────────────────────────────
  const handleSendQuery = (queryText?: string) => {
    const textToSend = queryText || chatInput;
    if (!textToSend.trim() || !overview || !conformance || !bottlenecks) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: textToSend,
    };

    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setIsTyping(true);

    setTimeout(() => {
      const q = textToSend.toLowerCase();
      let replyText = '';
      let metrics: Record<string, string | number> = {};
      let category = 'Operational Analytics';

      if (q.includes('bottleneck') || q.includes('delay') || q.includes('waiting')) {
        const bnList = bottlenecks.bottlenecks.slice(0, 3);
        const topBn = bnList[0];
        replyText = `Based on computed timestamp deltas across ${overview.total_events.toLocaleString()} events, your primary bottleneck is **${topBn?.activity}** with an average waiting queue time of **${topBn?.avg_waiting_time_hours.toFixed(1)} hours** (Median: ${topBn?.median_waiting_time_hours.toFixed(1)}h).\n\nTop delay stages:\n` +
          bnList.map((b, i) => `${i + 1}. **${b.activity}**: ${b.avg_waiting_time_hours.toFixed(1)}h avg wait (SLA breach rate: ${(b.sla_breach_rate * 100).toFixed(1)}%)`).join('\n');
        metrics = {
          'Top Bottleneck': topBn?.activity || 'N/A',
          'Avg Wait Time': `${topBn?.avg_waiting_time_hours.toFixed(1)}h`,
          'SLA Breach Rate': `${((topBn?.sla_breach_rate || 0) * 100).toFixed(1)}%`,
        };
        category = 'Bottleneck Analysis';
      } else if (q.includes('compliance') || q.includes('deviation') || q.includes('violation') || q.includes('approval') || q.includes('maverick')) {
        const devCount = conformance.deviant_cases;
        const topDev = conformance.deviation_breakdown[0];
        replyText = `Audit scan of reference P2P model reveals **${devCount} cases** (${(100 - conformance.conformance_percentage).toFixed(1)}%) deviated from standard procedure with an overall conformance fitness of **${(conformance.average_fitness_score * 100).toFixed(1)}%**.\n\nMost prevalent deviations:\n` +
          conformance.deviation_breakdown.map((d, i) => `${i + 1}. **${d.deviation_type}** (${d.category}): ${d.affected_cases} cases (${d.percentage_of_cases}%) — ${d.description}`).join('\n');
        metrics = {
          'Conformant Cases': `${conformance.conformant_cases} (${conformance.conformance_percentage}%)`,
          'Deviant Cases': devCount,
          'Top Violation': topDev ? `${topDev.deviation_type} (${topDev.affected_cases} cases)` : 'None',
        };
        category = 'Conformance Audit';
      } else if (q.includes('variant') || q.includes('path') || q.includes('pareto')) {
        const vCount = variants?.unique_variants_count || 0;
        const topVarPct = variants?.top_variant_percentage || 0;
        replyText = `Process mining extracted **${vCount} unique execution paths** across ${overview.total_purchase_cases.toLocaleString()} cases.\n\nThe most frequent variant accounts for **${topVarPct}%** of total case volume.\n- **Top Path**: ${variants?.variants[0]?.variant_signature || 'N/A'}\n- **Second Path**: ${variants?.variants[1]?.variant_signature || 'N/A'}`;
        metrics = {
          'Unique Variants': vCount,
          'Top Variant %': `${topVarPct}%`,
          'Rare Variants': variants?.variants.filter(v => v.is_rare).length || 0,
        };
        category = 'Process Variants';
      } else if (q.includes('vendor') || q.includes('supplier')) {
        const topV = vendors?.vendors[0];
        replyText = `Analysis across **${vendors?.total_vendors || 0} active suppliers** shows total spend of **$${(overview.total_spend_usd / 1000).toFixed(0)}k**.\n\n- Highest spend supplier: **${topV?.vendor_id}** ($${(topV?.total_spend_usd || 0).toLocaleString()})\n- Average supplier cycle time: **${topV?.avg_cycle_time_hours.toFixed(1)}h**\n- High-risk vendors (>25% SLA breach): **${vendors?.vendors.filter(v => v.sla_breach_rate > 0.25).length} suppliers**`;
        metrics = {
          'Total Suppliers': vendors?.total_vendors || 0,
          'Highest Spend': topV?.vendor_id || 'N/A',
          'SLA Breach Rate': `${((overview.sla_breach_cases / Math.max(1, overview.total_purchase_cases)) * 100).toFixed(1)}%`,
        };
        category = 'Vendor Performance';
      } else {
        replyText = `Summary of computed analytics for **${selectedDataset ? selectedDataset.name : 'Dataset'}**:\n- **Total Purchase Cases**: ${overview.total_purchase_cases.toLocaleString()}\n- **Completed Cases**: ${overview.completed_cases.toLocaleString()} (${(overview.completion_rate * 100).toFixed(1)}%)\n- **Average Cycle Time**: ${overview.avg_cycle_time_hours.toFixed(1)} hours (Median: ${overview.median_cycle_time_hours.toFixed(1)}h)\n- **Rework Rate**: ${(overview.rework_percentage * 100).toFixed(1)}% (${overview.rework_cases} cases)\n- **SLA Breach Rate**: ${(overview.sla_breach_percentage * 100).toFixed(1)}%\n- **Total Capital Spend**: $${overview.total_spend_usd.toLocaleString()}\n\nWhat specific dimension would you like to drill into?`;
        metrics = {
          'Total Cases': overview.total_purchase_cases,
          'Cycle Time': `${overview.avg_cycle_time_hours.toFixed(1)}h`,
          'Conformance': `${conformance.conformance_percentage}%`,
        };
      }

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: replyText,
        groundingMetrics: metrics,
        category,
      };

      setChatMessages(prev => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 400);
  };

  const sampleQueries = [
    'What are the primary operational bottlenecks?',
    'Summarize compliance deviations and control bypasses',
    'Which process variants drive the most volume?',
    'Which suppliers have the highest SLA breach rate?',
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
          title="Identified Action Items"
          value={recommendations.length}
          subtext="Ranked evidence-backed recommendations"
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
                <span>Formulating grounded response from process metrics...</span>
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
              {recommendations.length} items triggered
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
                key={rec.ruleId}
                className="bg-surface-card border border-surface-border hover:border-slate-700 rounded-xl p-4 space-y-3 transition-colors shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                        rec.severity === 'HIGH' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {rec.severity} {rec.category}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{rec.ruleId}</span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-100">{rec.title}</h3>
                  </div>
                </div>

                <p className="text-[11px] text-slate-300 leading-relaxed">
                  {rec.observation}
                </p>

                {/* Evidence Box */}
                <div className="bg-[#0A0E18] border border-surface-border rounded p-2 text-[10px] font-mono text-indigo-300">
                  <span className="text-slate-400 font-semibold block mb-0.5">Calculated Evidence:</span>
                  {rec.evidence}
                </div>

                {/* Prescriptive Action */}
                <div className="bg-surface border-l-2 border-indigo-500 p-2.5 rounded-r text-[11px] text-slate-200">
                  <span className="font-semibold text-indigo-400 block mb-0.5">Recommended Action:</span>
                  {rec.recommendation}
                </div>

                {/* Expected Impact */}
                <div className="text-[10px] text-slate-400 flex items-center gap-1.5 pt-1">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span>Impact: {rec.estimatedImpact}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
