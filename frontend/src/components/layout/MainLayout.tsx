import React from 'react';
import { Header } from './Header';
import { NavTab, Sidebar } from './Sidebar';

interface MainLayoutProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  activeTab,
  onSelectTab,
  children,
}) => {
  return (
    <div className="flex min-h-screen bg-background text-slate-100 font-sans selection:bg-blue-500/30 selection:text-blue-200">
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
