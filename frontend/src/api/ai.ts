import { apiClient } from './client';
import { RecommendationsResponse } from '../types/api';

export interface RecommendationsFilterParams {
  dataset_id: string;
  start_date?: string;
  end_date?: string;
  skip_approval_threshold?: number;
  early_invoice_threshold?: number;
  skip_verification_threshold?: number;
  high_rework_threshold?: number;
  approval_bottleneck_hours?: number;
  low_fpy_threshold?: number;
  high_abandonment_threshold?: number;
  sla_breach_threshold?: number;
  sla_hours?: number;
}

export const aiApi = {
  getRecommendations: async (params: RecommendationsFilterParams) => {
    return apiClient<RecommendationsResponse>('/ai/recommendations', { params });
  },
};
