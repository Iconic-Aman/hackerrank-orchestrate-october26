import type { CaseDetailResponse, CaseListResponse, StatsResponse } from "../types";

export function getApiConfig(): { baseUrl: string; secretKey: string } {
  const envUrl = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL;
  const baseUrl = localStorage.getItem("API_BASE_URL") || envUrl || "/api/v1";
  const secretKey = localStorage.getItem("SECRET_KEY") || import.meta.env.VITE_SECRET_KEY || "";
  return { baseUrl: baseUrl.replace(/\/$/, ""), secretKey };
}


export function saveApiConfig(baseUrl: string, secretKey: string): void {
  localStorage.setItem("API_BASE_URL", baseUrl);
  localStorage.setItem("SECRET_KEY", secretKey);
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const { baseUrl, secretKey } = getApiConfig();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (secretKey) {
    headers.set("Authorization", `Bearer ${secretKey}`);
  }

  const url = `${baseUrl}${endpoint}`;
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCases: (offset = 0, limit = 50, search?: string, status?: string) => {
    const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
    if (search) params.append("search", search);
    if (status) params.append("status", status);
    return request<CaseListResponse>(`/cases?${params.toString()}`);
  },

  getCaseDetail: (caseId: string) => {
    return request<CaseDetailResponse>(`/cases/${caseId}`);
  },

  auditCase: (caseId: string) => {
    return request<CaseDetailResponse>(`/cases/${caseId}/audit`, { method: "POST" });
  },

  getStats: () => {
    return request<StatsResponse>("/stats");
  },

  runBatchAudit: () => {
    return request<{ total_cases: number; complete: number; incomplete: number; not_applicable: number; duration_seconds: number }>("/audit/run", { method: "POST" });
  },
};
