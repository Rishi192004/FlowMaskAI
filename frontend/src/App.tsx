import React, { useState } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import { NavTab } from './components/layout/Sidebar';
import { FilterProvider } from './context/FilterContext';
import { AIProcessAssistant } from './pages/AIProcessAssistant';
import { BottleneckAnalysis } from './pages/BottleneckAnalysis';
import { ConformanceChecking } from './pages/ConformanceChecking';
import { DataQualityReportPage } from './pages/DataQualityReport';
import { DatasetManagement } from './pages/DatasetManagement';
import { ETLProcessing } from './pages/ETLProcessing';
import { OverviewDashboard } from './pages/OverviewDashboard';
import { ProcessDiscovery } from './pages/ProcessDiscovery';
import { VariantExplorer } from './pages/VariantExplorer';
import { VendorPerformance } from './pages/VendorPerformance';

export const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');

  const renderActivePage = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewDashboard />;
      case 'bottlenecks':
        return <BottleneckAnalysis />;
      case 'vendors':
        return <VendorPerformance />;
      case 'discovery':
        return <ProcessDiscovery />;
      case 'variants':
        return <VariantExplorer />;
      case 'conformance':
        return <ConformanceChecking />;
      case 'datasets':
        return <DatasetManagement onNavigateToETL={() => setActiveTab('etl')} />;
      case 'etl':
        return <ETLProcessing onNavigateToQuality={() => setActiveTab('quality')} />;
      case 'quality':
        return <DataQualityReportPage />;
      case 'assistant':
        return <AIProcessAssistant />;
      default:
        return <OverviewDashboard />;
    }
  };

  return (
    <MainLayout activeTab={activeTab} onSelectTab={setActiveTab}>
      {renderActivePage()}
    </MainLayout>
  );
};

export const App: React.FC = () => {
  return (
    <FilterProvider>
      <AppContent />
    </FilterProvider>
  );
};

export default App;
