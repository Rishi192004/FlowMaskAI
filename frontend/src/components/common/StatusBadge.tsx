import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toLowerCase();

  let colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';

  if (['completed', 'conformant', 'processed', 'ok', 'low', 'success'].includes(normalized)) {
    colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  } else if (['processing', 'running', 'medium', 'warning', 'uploaded'].includes(normalized)) {
    colorClasses = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  } else if (['failed', 'deviant', 'high', 'error', 'danger', 'rejected'].includes(normalized)) {
    colorClasses = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  } else if (['info', 'incomplete'].includes(normalized)) {
    colorClasses = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  }

  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center font-medium rounded-full border ${sizeClasses} ${colorClasses}`}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {status}
    </span>
  );
};
