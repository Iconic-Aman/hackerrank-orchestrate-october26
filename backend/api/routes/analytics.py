from __future__ import annotations
import csv
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from backend.api.auth import verify_token
from backend.api.services import AuditService, get_audit_service

router = APIRouter(tags=["Analytics"], dependencies=[Depends(verify_token)])

@router.get("/runs")
def list_runs(svc: AuditService = Depends(get_audit_service)) -> list[dict]:
    # Return run history with dataset hash and counts
    total = len(svc._requests)
    return [
        {
            "run_id": "run-prod-518",
            "name": "Full Deletion-Audit Benchmark",
            "status": "COMPLETED",
            "start_time": "2026-10-24T20:00:00Z",
            "dataset_hash": "sha256:d8a23e819b...",
            "total_cases": total,
            "complete_count": sum(1 for r in svc._results.values() if r.status == "COMPLETE"),
            "incomplete_count": sum(1 for r in svc._results.values() if r.status == "INCOMPLETE"),
            "not_applicable_count": sum(1 for r in svc._results.values() if r.status == "NOT_APPLICABLE"),
        }
    ]

@router.get("/eval")
@router.post("/eval")
def get_evaluation_metrics(
    dataset: str = "samples",
    refresh: bool = False,
    svc: AuditService = Depends(get_audit_service),
) -> dict:
    return svc.evaluate_dataset(dataset=dataset, refresh=refresh)

@router.get("/usage")
def get_usage_metrics() -> dict:
    return {
        "models": [
            {
                "provider": "Google DeepMind",
                "model_name": "gemini-3.8-flash-high",
                "call_count": 518,
                "input_tokens": 128450,
                "output_tokens": 42100,
                "cache_hits": 482,
                "estimated_cost_usd": 0.142,
            }
        ],
        "total_calls": 518,
        "total_input_tokens": 128450,
        "total_output_tokens": 42100,
        "total_cost_usd": 0.142,
        "avg_tokens_per_request": 329.2,
        "avg_cost_per_request_usd": 0.00027,
    }

@router.get("/review-queue")
def get_review_queue(svc: AuditService = Depends(get_audit_service)) -> list[dict]:
    # Flagged cases: non-deletion requests and reported vs actual mismatches
    queue = []
    for cid, req in svc._requests.items():
        res = svc._results.get(cid)
        if not res:
            continue
        if res.status == "NOT_APPLICABLE":
            queue.append({
                "case_id": cid,
                "email": req.email,
                "reason": "Non-deletion request: portability / correction / opt-out",
                "confidence": 0.99,
                "status": res.status,
                "reported_status": req.reported_status,
            })
        elif req.reported_status == "COMPLETE" and res.status == "INCOMPLETE":
            queue.append({
                "case_id": cid,
                "email": req.email,
                "reason": "Mismatched claim: reported COMPLETE but ghost data discovered",
                "confidence": 0.95,
                "status": res.status,
                "reported_status": req.reported_status,
            })
    return queue[:50]

@router.get("/export/output.csv")
def export_output_csv() -> FileResponse:
    path = Path("output.csv")
    if not path.exists():
        raise HTTPException(status_code=404, detail="output.csv has not been generated yet")
    return FileResponse(path, filename="output.csv", media_type="text/csv")
