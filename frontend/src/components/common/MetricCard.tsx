import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  };
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtext,
  icon,
  badge,
  className = '',
}) => {
  const badgeStyles = {
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    danger: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    neutral: 'bg-slate-700/30 text-slate-400 border-slate-700/50',
  };

  return (
    <div className={`bg-surface-card border border-surface-border rounded-xl p-5 shadow-sm hover:border-slate-700 transition-colors ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</span>
        {icon && <div className="text-slate-400 p-2 bg-surface rounded-lg border border-surface-border">{icon}</div>}
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div className="text-2xl font-semibold text-slate-100 tracking-tight font-mono">{value}</div>
        {badge && (
          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${badgeStyles[badge.variant]}`}>
            {badge.text}
          </span>
        )}
      </div>

      {subtext && <p className="mt-1.5 text-xs text-slate-500">{subtext}</p>}
    </div>
  );
};
