export interface Step {
  step_no: number;
  phase: "FINDING" | "REMEDIATION" | "VERIFICATION";
  system_id: string;
  resource_id: string;
  operation: string;
  state: string;
  evidence_id: string;
}

export interface CaseSummary {
  case_id: string;
  email: string;
  requested_at: string;
  reported_status: string;
  audit_at: string;
  status: string | null;
}

export interface CaseListResponse {
  total: number;
  offset: number;
  limit: number;
  cases: CaseSummary[];
}

export interface CaseDetailResponse {
  case_id: string;
  email: string;
  requested_at: string;
  reported_status: string;
  reported_at: string;
  audit_at: string;
  request_text: string;
  status: string;
  steps: Step[];
}

export interface StatsResponse {
  total_cases: number;
  complete_count: number;
  incomplete_count: number;
  not_applicable_count: number;
  findings_by_operation: Record<string, number>;
}

export interface RunItem {
  run_id: string;
  name: string;
  status: "RUNNING" | "COMPLETED" | "CANCELLED" | "FAILED";
  start_time: string;
  dataset_hash: string;
  total_cases: number;
  complete_count: number;
  incomplete_count: number;
  not_applicable_count: number;
}

export interface FailedCaseDiff {
  case_id: string;
  reason: string;
  expected_steps: Partial<Step>[];
  actual_steps: Partial<Step>[];
}

export interface EvalMetrics {
  dataset: string;
  status_accuracy: number;
  step_accuracy: number;
  field_accuracy: number;
  sequence_accuracy: number;
  dev_score: number;
  holdout_score: number;
  failed_cases: FailedCaseDiff[];
}

export interface ModelUsage {
  provider: string;
  model_name: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  cache_hits: number;
  estimated_cost_usd: number;
}

export interface UsageMetrics {
  models: ModelUsage[];
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_tokens_per_request: number;
  avg_cost_per_request_usd: number;
}

export interface ReviewItem {
  case_id: string;
  email: string;
  reason: string;
  confidence: number;
  status: string;
  reported_status: string;
}
