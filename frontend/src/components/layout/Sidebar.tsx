import React from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  Brain,
  Building2,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  GitFork,
  LayoutDashboard,
  Timer,
} from 'lucide-react';

export type NavTab =
  | 'overview'
  | 'datasets'
  | 'etl'
  | 'quality'
  | 'discovery'
  | 'variants'
  | 'conformance'
  | 'bottlenecks'
  | 'vendors'
  | 'assistant';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

interface NavItem {
  id: NavTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  const navSections: NavSection[] = [
    {
      title: 'Operational Monitoring',
      items: [
        { id: 'overview' as NavTab, label: 'Overview Dashboard', icon: LayoutDashboard },
        { id: 'bottlenecks' as NavTab, label: 'Bottleneck Analysis', icon: Timer },
        { id: 'vendors' as NavTab, label: 'Vendor Performance', icon: Building2 },
      ],
    },
    {
      title: 'Process Mining',
      items: [
        { id: 'discovery' as NavTab, label: 'Process Discovery', icon: Activity },
        { id: 'variants' as NavTab, label: 'Variant Explorer', icon: GitFork },
        { id: 'conformance' as NavTab, label: 'Conformance & Audit', icon: CheckCircle2 },
      ],
    },
    {
      title: 'Data & ETL Engine',
      items: [
        { id: 'datasets' as NavTab, label: 'Dataset Management', icon: Database },
        { id: 'etl' as NavTab, label: 'ETL Processing', icon: FileSpreadsheet },
        { id: 'quality' as NavTab, label: 'Data Quality Report', icon: AlertTriangle },
      ],
    },
    {
      title: 'Intelligence',
      items: [
        { id: 'assistant' as NavTab, label: 'AI Process Assistant', icon: Bot, badge: 'Grounded' },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-[#0D1322] border-r border-surface-border flex flex-col flex-shrink-0 min-h-screen">
      {/* Brand Logo Header */}
      <div className="p-5 border-b border-surface-border flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/10">
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
            FlowMind <span className="text-[10px] bg-blue-500/20 text-blue-400 font-mono px-1.5 py-0.2 rounded border border-blue-500/30">PROD</span>
          </h1>
          <p className="text-[11px] text-slate-500">Process Mining & Operational Analytics</p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 py-4 px-3 space-y-6 overflow-y-auto">
        {navSections.map(section => (
          <div key={section.title}>
            <div className="px-3 mb-2 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
              {section.title}
            </div>
            <div className="space-y-1">
              {section.items.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-surface-hover/80'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        isActive ? 'bg-blue-700 text-white' : 'bg-surface text-slate-400 border border-surface-border'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-surface-border text-[11px] text-slate-500">
        <div className="flex items-center justify-between mb-1">
          <span>Engine Status</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
          </span>
        </div>
        <div className="text-[10px] font-mono text-slate-600">PostgreSQL + PM4Py 2.7</div>
      </div>
    </aside>
  );
};
