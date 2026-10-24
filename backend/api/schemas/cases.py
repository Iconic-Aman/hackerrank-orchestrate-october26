from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from backend.agent.models import Step

class CaseSummary(BaseModel):
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    audit_at: datetime
    status: str | None = None

class CaseListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    cases: list[CaseSummary]

class CaseDetailResponse(BaseModel):
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str
    status: str
    steps: list[Step] = Field(default_factory=list)

class AuditRunResponse(BaseModel):
    total_cases: int
    complete: int
    incomplete: int
    not_applicable: int
    duration_seconds: float

class StatsResponse(BaseModel):
    total_cases: int
    complete_count: int
    incomplete_count: int
    not_applicable_count: int
    findings_by_operation: dict[str, int] = Field(default_factory=dict)
