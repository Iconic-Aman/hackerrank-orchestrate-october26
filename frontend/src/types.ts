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
