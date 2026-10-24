from __future__ import annotations
from fastapi import APIRouter, Depends
from backend.api.schemas.cases import AuditRunResponse
from backend.api.services import AuditService, get_audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.post("/run", response_model=AuditRunResponse)
def run_batch_audit(
    svc: AuditService = Depends(get_audit_service),
) -> AuditRunResponse:
    counts, duration = svc.run_all()
    return AuditRunResponse(
        total_cases=counts["total_cases"],
        complete=counts["complete"],
        incomplete=counts["incomplete"],
        not_applicable=counts["not_applicable"],
        duration_seconds=round(duration, 3),
    )
