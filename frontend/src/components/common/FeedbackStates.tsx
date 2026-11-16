import React from 'react';

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading analytics data...' }) => {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <div className="w-10 h-10 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mb-4" />
      <p className="text-sm text-slate-400 font-medium">{message}</p>
    </div>
  );
};

export const EmptyState: React.FC<{
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}> = ({ title, description, action }) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-surface-card border border-surface-border rounded-xl">
      <div className="w-12 h-12 rounded-full bg-surface border border-surface-border flex items-center justify-center text-slate-400 mb-4">
        📂
      </div>
      <h3 className="text-base font-semibold text-slate-200">{title}</h3>
      <p className="mt-1 text-sm text-slate-400 max-w-md">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 px-4 py-2 bg-brand-primary hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
}> = ({ title = 'Failed to load data', message, onRetry }) => {
  return (
    <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-xl my-4 text-slate-200">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-sm font-semibold text-rose-400">{title}</h4>
          <p className="mt-1 text-xs text-slate-400 font-mono">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs rounded-md font-medium transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
};
