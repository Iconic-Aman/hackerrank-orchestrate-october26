from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.api.schemas.cases import CaseDetailResponse, CaseListResponse
from backend.api.services import AuditService, get_audit_service

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.get("", response_model=CaseListResponse)
def list_cases(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    status: str | None = Query(None),
    svc: AuditService = Depends(get_audit_service),
) -> CaseListResponse:
    total, cases = svc.list_cases(offset=offset, limit=limit, search=search, status=status)
    return CaseListResponse(total=total, offset=offset, limit=limit, cases=cases)

@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str,
    svc: AuditService = Depends(get_audit_service),
) -> CaseDetailResponse:
    detail = svc.get_case(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return detail

@router.post("/{case_id}/audit", response_model=CaseDetailResponse)
def audit_case(
    case_id: str,
    svc: AuditService = Depends(get_audit_service),
) -> CaseDetailResponse:
    detail = svc.audit_single_case(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return detail
