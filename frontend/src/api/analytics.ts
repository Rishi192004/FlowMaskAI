import { apiClient } from './client';
import {
  BottlenecksResponse,
  CycleTimeMetrics,
  DepartmentPerformanceResponse,
  OverviewMetrics,
  ReworkMetrics,
  TrendsResponse,
  VendorPerformanceResponse,
  WaitingTimeMetrics,
} from '../types/api';

export interface AnalyticsFilterParams {
  dataset_id: string;
  start_date?: string;
  end_date?: string;
  sla_hours?: number;
  activity_sla_hours?: number;
}

export const analyticsApi = {
  getOverview: async (params: AnalyticsFilterParams) => {
    return apiClient<OverviewMetrics>('/analytics/overview', { params });
  },

  getCycleTime: async (params: AnalyticsFilterParams) => {
    return apiClient<CycleTimeMetrics>('/analytics/cycle-time', { params });
  },

  getWaitingTime: async (params: AnalyticsFilterParams) => {
    return apiClient<WaitingTimeMetrics>('/analytics/waiting-time', { params });
  },

  getRework: async (params: AnalyticsFilterParams) => {
    return apiClient<ReworkMetrics>('/analytics/rework', { params });
  },

  getBottlenecks: async (params: AnalyticsFilterParams) => {
    return apiClient<BottlenecksResponse>('/analytics/bottlenecks', { params });
  },

  getVendorPerformance: async (params: AnalyticsFilterParams) => {
    return apiClient<VendorPerformanceResponse>('/analytics/vendor-performance', { params });
  },

  getDepartmentPerformance: async (params: AnalyticsFilterParams) => {
    return apiClient<DepartmentPerformanceResponse>('/analytics/department-performance', { params });
  },

  getTrends: async (params: AnalyticsFilterParams) => {
    return apiClient<TrendsResponse>('/analytics/trends', { params });
  },
};
