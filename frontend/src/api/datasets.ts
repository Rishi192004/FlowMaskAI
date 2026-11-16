import { apiClient } from './client';
import {
  DataQualityReport,
  Dataset,
  DatasetUploadResponse,
  ETLExecutionSummary,
} from '../types/api';

export const datasetsApi = {
  list: async (page = 1, pageSize = 50) => {
    return apiClient<{ items: Dataset[]; total: number; page: number; page_size: number; pages: number }>(
      '/datasets',
      { params: { page, page_size: pageSize } }
    );
  },

  get: async (datasetId: string) => {
    return apiClient<Dataset>(`/datasets/${datasetId}`);
  },

  upload: async (file: File, name?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }
    return apiClient<DatasetUploadResponse>('/datasets/upload', {
      method: 'POST',
      body: formData,
    });
  },

  getQuality: async (datasetId: string) => {
    return apiClient<DataQualityReport>(`/datasets/${datasetId}/quality`);
  },

  process: async (
    datasetId: string,
    options?: {
      column_mapping?: Record<string, string>;
      delimiter?: string;
      normalize_activities?: boolean;
      drop_duplicates?: boolean;
    }
  ) => {
    return apiClient<{
      dataset_id: string;
      execution_id: string;
      status: string;
      message: string;
      metrics: Record<string, number>;
      duration_seconds: number;
    }>(`/datasets/${datasetId}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {}),
    });
  },
};
