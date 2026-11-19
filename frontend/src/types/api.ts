export interface Dataset {
  id: string;
  name: string;
  filename: string;
  file_size_bytes: number;
  delimiter: string;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  total_rows_raw: number;
  column_mapping?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface DatasetUploadResponse {
  id: string;
  name: string;
  filename: string;
  file_size_bytes: number;
  delimiter: string;
  status: string;
  detected_columns: string[];
  suggested_mapping: Record<string, string>;
  preview_rows: Record<string, any>[];
  created_at: string;
}

export interface ETLExecutionSummary {
  id: string;
  dataset_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  total_records_received: number;
  valid_records: number;
  duplicate_records: number;
  invalid_records: number;
  missing_value_records: number;
  records_rejected: number;
  records_loaded: number;
  error_message?: string;
}

export interface DataQualityIssueItem {
  id: number;
  row_index: number;
  issue_type: string;
  severity: 'ERROR' | 'WARNING' | 'INFO';
  details: Record<string, any>;
  is_fatal: boolean;
  created_at: string;
}

export interface DataQualityReport {
  dataset_id: string;
  dataset_name: string;
  dataset_status: string;
  latest_execution?: ETLExecutionSummary;
  metrics: {
    total_records_received: number;
    valid_records: number;
    duplicate_records: number;
    invalid_records: number;
    missing_value_records: number;
    records_rejected: number;
    records_loaded: number;
  };
  issue_breakdown: Record<string, number>;
  recent_issues: DataQualityIssueItem[];
}

export interface OverviewMetrics {
  dataset_id: string;
  total_purchase_cases: number;
  total_events: number;
  completed_cases: number;
  incomplete_cases: number;
  completion_rate: number;
  avg_cycle_time_hours: number;
  median_cycle_time_hours: number;
  p90_cycle_time_hours: number;
  rework_cases: number;
  rework_percentage: number;
  sla_hours: number;
  sla_breach_cases: number;
  sla_breach_percentage: number;
  total_spend_usd: number;
  start_date?: string;
  end_date?: string;
}

export interface CycleTimeDistributionBin {
  bin_start_hours: number;
  bin_end_hours: number;
  case_count: number;
}

export interface CycleTimeMetrics {
  dataset_id: string;
  total_cases: number;
  completed_cases: number;
  avg_cycle_time_hours: number;
  median_cycle_time_hours: number;
  p75_cycle_time_hours: number;
  p90_cycle_time_hours: number;
  p95_cycle_time_hours: number;
  min_cycle_time_hours: number;
  max_cycle_time_hours: number;
  sla_hours: number;
  sla_breach_count: number;
  sla_breach_percentage: number;
  distribution: CycleTimeDistributionBin[];
}

export interface ActivityTimeMetric {
  activity: string;
  transition_count: number;
  avg_waiting_time_hours: number;
  median_waiting_time_hours: number;
  p90_waiting_time_hours: number;
  min_waiting_time_hours: number;
  max_waiting_time_hours: number;
  total_waiting_time_hours: number;
}

export interface WaitingTimeMetrics {
  dataset_id: string;
  overall_avg_waiting_time_hours: number;
  activities: ActivityTimeMetric[];
}

export interface ActivityReworkMetric {
  activity: string;
  rework_case_count: number;
  total_rework_occurrences: number;
  rework_rate: number;
  max_repetitions_in_case: number;
}

export interface ReworkMetrics {
  dataset_id: string;
  total_cases: number;
  cases_with_rework: number;
  rework_case_percentage: number;
  total_rework_events: number;
  activities: ActivityReworkMetric[];
}

export interface BottleneckItem {
  rank: number;
  activity: string;
  bottleneck_score: number;
  avg_waiting_time_hours: number;
  median_waiting_time_hours: number;
  rework_rate: number;
  sla_breach_rate: number;
  transition_count: number;
  reasons: string[];
}

export interface BottlenecksResponse {
  dataset_id: string;
  top_bottleneck?: string;
  ranking_methodology: string;
  bottlenecks: BottleneckItem[];
}

export interface VendorPerformanceItem {
  vendor_id: string;
  total_cases: number;
  total_spend_usd: number;
  avg_cycle_time_hours: number;
  median_cycle_time_hours: number;
  sla_breach_count: number;
  sla_breach_rate: number;
  completed_cases: number;
  completion_rate: number;
}

export interface VendorPerformanceResponse {
  dataset_id: string;
  total_vendors: number;
  vendors: VendorPerformanceItem[];
}

export interface DepartmentPerformanceItem {
  department: string;
  total_cases: number;
  total_spend_usd: number;
  avg_cycle_time_hours: number;
  rework_cases: number;
  rework_rate: number;
  completed_cases: number;
  completion_rate: number;
}

export interface DepartmentPerformanceResponse {
  dataset_id: string;
  total_departments: number;
  departments: DepartmentPerformanceItem[];
}

export interface MonthlyTrendItem {
  month: string;
  case_volume: number;
  completed_cases: number;
  total_events: number;
  total_spend_usd: number;
  avg_cycle_time_hours: number;
  sla_breach_rate: number;
}

export interface TrendsResponse {
  dataset_id: string;
  trends: MonthlyTrendItem[];
}

export interface ProcessMapNode {
  id: string;
  label: string;
  frequency: number;
  avg_duration_hours: number;
  is_start: boolean;
  is_end: boolean;
  is_bottleneck: boolean;
}

export interface ProcessMapEdge {
  id: string;
  source: string;
  target: string;
  frequency: number;
  avg_duration_hours: number;
  median_duration_hours: number;
  is_bottleneck: boolean;
}

export interface ProcessMapResponse {
  dataset_id: string;
  total_cases: number;
  total_events: number;
  nodes: ProcessMapNode[];
  edges: ProcessMapEdge[];
  start_activities: Record<string, number>;
  end_activities: Record<string, number>;
}

export interface PetriNetPlace {
  id: string;
  name: string;
}

export interface PetriNetTransition {
  id: string;
  label?: string | null;
}

export interface PetriNetArc {
  source: string;
  target: string;
}

export interface ProcessDiscoveryResponse {
  dataset_id: string;
  algorithm: string;
  places: PetriNetPlace[];
  transitions: PetriNetTransition[];
  arcs: PetriNetArc[];
  start_activities: Record<string, number>;
  end_activities: Record<string, number>;
  process_tree_repr?: string | null;
}

export interface DFGTransition {
  source: string;
  target: string;
  frequency: number;
  avg_duration_hours: number;
}

export interface DFGResponse {
  dataset_id: string;
  total_cases: number;
  total_events: number;
  transitions: DFGTransition[];
  start_activities: Record<string, number>;
  end_activities: Record<string, number>;
}

export interface ProcessVariantItem {
  variant_id: number;
  activities: string[];
  variant_signature: string;
  case_count: number;
  percentage: number;
  is_rare: boolean;
  sample_case_ids: string[];
}

export interface ProcessVariantsResponse {
  dataset_id: string;
  total_cases: number;
  unique_variants_count: number;
  top_variant_percentage: number;
  variants: ProcessVariantItem[];
  excessive_activity_cases: Array<{
    case_id: string;
    event_count: number;
    threshold: number;
    reason: string;
  }>;
}

export interface ActivityFrequencyItem {
  activity: string;
  event_count: number;
  case_count: number;
  case_coverage_percentage: number;
  is_start: boolean;
  is_end: boolean;
}

export interface ActivityFrequencyResponse {
  dataset_id: string;
  total_events: number;
  total_cases: number;
  activities: ActivityFrequencyItem[];
}

export interface ComparisonSliceMetrics {
  label: string;
  case_count: number;
  event_count: number;
  unique_variants: number;
  avg_cycle_time_hours: number;
  top_variant?: string;
}

export interface ComparisonResponse {
  dataset_id: string;
  slice_a: ComparisonSliceMetrics;
  slice_b: ComparisonSliceMetrics;
  shared_activities: string[];
  unique_to_a: string[];
  unique_to_b: string[];
  divergence_summary: string;
}

export interface ConformanceRulesConfig {
  reference_sequence: string[];
  require_manager_approval: boolean;
  prohibit_early_invoice_verification: boolean;
  allow_repeated_approval: boolean;
  require_payment_completion: boolean;
  prohibit_unexpected_activities: boolean;
  strict_sequence: boolean;
}

export interface CaseDeviationDetail {
  deviation_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  culprit_activity: string;
  culprit_event_id?: number;
  culprit_timestamp?: string;
  expected: string;
  actual: string;
}

export interface CaseDeviationItem {
  case_id: string;
  is_conformant: boolean;
  fitness_score: number;
  total_events: number;
  duration_hours: number;
  deviations: CaseDeviationDetail[];
}

export interface CaseDeviationsListResponse {
  dataset_id: string;
  total_cases: number;
  conformant_cases_count: number;
  deviant_cases_count: number;
  page: number;
  page_size: number;
  pages: number;
  cases: CaseDeviationItem[];
}

export interface DeviationSummaryItem {
  deviation_type: string;
  category: string;
  severity: string;
  affected_cases: number;
  percentage_of_cases: number;
  description: string;
}

export interface ConformanceOverviewResponse {
  dataset_id: string;
  total_cases: number;
  conformant_cases: number;
  deviant_cases: number;
  conformance_percentage: number;
  average_fitness_score: number;
  deviation_breakdown: DeviationSummaryItem[];
  active_rules: ConformanceRulesConfig;
}
