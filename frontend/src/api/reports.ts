import { apiDownload, ApiDownload } from './client';

export interface ReportFilterParams {
  dataset_id: string;
  start_date?: string;
  end_date?: string;
}

const withInclusiveEndDate = (value?: string) => {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return `${value}T23:59:59.999999`;
  }
  return value;
};

const downloadReport = (
  report: string,
  params: ReportFilterParams,
): Promise<ApiDownload> => apiDownload(`/reports/${report}`, {
  ...params,
  end_date: withInclusiveEndDate(params.end_date),
});

export const reportsApi = {
  downloadEventsCsv: (params: ReportFilterParams) => downloadReport('events-csv', params),
  downloadKpiPdf: (params: ReportFilterParams) => downloadReport('kpi-pdf', params),
  downloadConformanceJson: (params: ReportFilterParams) => downloadReport('conformance-json', params),
};
