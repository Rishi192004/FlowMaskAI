import { apiClient } from './client';
import {
  ActivityFrequencyResponse,
  ComparisonResponse,
  DFGResponse,
  ProcessDiscoveryResponse,
  ProcessMapResponse,
  ProcessVariantsResponse,
} from '../types/api';

export interface ProcessFilterParams {
  dataset_id: string;
  start_date?: string;
  end_date?: string;
  department?: string;
  vendor_id?: string;
}

export const processApi = {
  getMap: async (params: ProcessFilterParams) => {
    return apiClient<ProcessMapResponse>('/process/map', { params });
  },

  getDFG: async (params: ProcessFilterParams) => {
    return apiClient<DFGResponse>('/process/dfg', { params });
  },

  getDiscovery: async (params: ProcessFilterParams) => {
    return apiClient<ProcessDiscoveryResponse>('/process/discovery', { params });
  },

  getVariants: async (params: ProcessFilterParams) => {
    return apiClient<ProcessVariantsResponse>('/process/variants', { params });
  },

  getActivities: async (params: ProcessFilterParams) => {
    return apiClient<ActivityFrequencyResponse>('/process/activities', { params });
  },

  compare: async (params: { dataset_id: string; dimension: 'department' | 'vendor'; value_a: string; value_b: string }) => {
    return apiClient<ComparisonResponse>('/process/compare', { params });
  },
};
