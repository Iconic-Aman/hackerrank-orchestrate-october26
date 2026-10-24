from __future__ import annotations
from fastapi import APIRouter, Depends
from backend.api.schemas.cases import StatsResponse
from backend.api.services import AuditService, get_audit_service

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("", response_model=StatsResponse)
def get_stats(
    svc: AuditService = Depends(get_audit_service),
) -> StatsResponse:
    return svc.get_stats()
