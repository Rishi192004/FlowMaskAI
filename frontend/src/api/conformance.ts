import { apiClient } from './client';
import {
  CaseDeviationsListResponse,
  ConformanceOverviewResponse,
  ConformanceRulesConfig,
  DeviationSummaryItem,
} from '../types/api';

export const conformanceApi = {
  getOverview: async (params: { dataset_id: string; start_date?: string; end_date?: string }) => {
    return apiClient<ConformanceOverviewResponse>('/conformance/overview', { params });
  },

  getDeviations: async (datasetId: string) => {
    return apiClient<DeviationSummaryItem[]>('/conformance/deviations', { params: { dataset_id: datasetId } });
  },

  getCases: async (params: {
    dataset_id: string;
    filter_deviant_only?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    return apiClient<CaseDeviationsListResponse>('/conformance/cases', { params });
  },

  getRules: async (datasetId: string) => {
    return apiClient<ConformanceRulesConfig>('/conformance/rules', { params: { dataset_id: datasetId } });
  },

  updateRules: async (datasetId: string, config: ConformanceRulesConfig) => {
    return apiClient<ConformanceRulesConfig>('/conformance/rules', {
      method: 'PUT',
      params: { dataset_id: datasetId },
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
  },
};
