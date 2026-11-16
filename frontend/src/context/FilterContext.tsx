import React, { createContext, useContext, useEffect, useState } from 'react';
import { Dataset } from '../types/api';
import { datasetsApi } from '../api/datasets';

interface FilterContextType {
  datasets: Dataset[];
  selectedDatasetId: string | null;
  selectedDataset: Dataset | null;
  setSelectedDatasetId: (id: string | null) => void;
  startDate: string;
  setStartDate: (d: string) => void;
  endDate: string;
  setEndDate: (d: string) => void;
  selectedDepartment: string;
  setSelectedDepartment: (dept: string) => void;
  selectedVendor: string;
  setSelectedVendor: (v: string) => void;
  isLoadingDatasets: boolean;
  refreshDatasets: () => Promise<void>;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export const FilterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [selectedDepartment, setSelectedDepartment] = useState<string>('');
  const [selectedVendor, setSelectedVendor] = useState<string>('');
  const [isLoadingDatasets, setIsLoadingDatasets] = useState<boolean>(true);

  const refreshDatasets = async () => {
    try {
      setIsLoadingDatasets(true);
      const res = await datasetsApi.list();
      setDatasets(res.items);
      // Auto-select first processed or available dataset if none selected
      if (!selectedDatasetId && res.items.length > 0) {
        const processed = res.items.find(d => d.status === 'processed') || res.items[0];
        setSelectedDatasetId(processed.id);
      }
    } catch (err) {
      console.error('Failed to load datasets:', err);
    } finally {
      setIsLoadingDatasets(false);
    }
  };

  useEffect(() => {
    refreshDatasets();
  }, []);

  const selectedDataset = datasets.find(d => d.id === selectedDatasetId) || null;

  return (
    <FilterContext.Provider
      value={{
        datasets,
        selectedDatasetId,
        selectedDataset,
        setSelectedDatasetId,
        startDate,
        setStartDate,
        endDate,
        setEndDate,
        selectedDepartment,
        setSelectedDepartment,
        selectedVendor,
        setSelectedVendor,
        isLoadingDatasets,
        refreshDatasets,
      }}
    >
      {children}
    </FilterContext.Provider>
  );
};

export const useFilters = () => {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useFilters must be used within a FilterProvider');
  }
  return context;
};
