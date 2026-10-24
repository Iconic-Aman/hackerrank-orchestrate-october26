from __future__ import annotations
import csv
import os
import time
from datetime import datetime
from pathlib import Path
from backend.agent.models import CaseResult, Request
from backend.agent.pipeline import AuditEngine
from backend.agent.stages.s10_output import write_output_csv
from backend.api.schemas.cases import CaseDetailResponse, CaseSummary, StatsResponse

def get_dataset_dir() -> Path:
    env_path = os.getenv("DATASET_DIR")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    for c in [Path("dataset"), Path("../dataset"), Path(__file__).resolve().parents[2] / "dataset"]:
        if c.exists():
            return c
    raise FileNotFoundError("Dataset directory not found")

class AuditService:
    def __init__(self) -> None:
        self.dataset_dir = get_dataset_dir()
        self._engine: AuditEngine | None = None
        self._requests: dict[str, Request] = {}
        self._results: dict[str, CaseResult] = {}
        self._load_requests()

    def _load_requests(self) -> None:
        csv_path = self.dataset_dir / "deletion_requests.csv"
        if not csv_path.exists():
            csv_path = self.dataset_dir / "sample_deletion_requests.csv"
        with open(csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                req = Request(
                    case_id=r["case_id"],
                    email=r["email"],
                    requested_at=datetime.fromisoformat(r["requested_at"].replace("Z", "+00:00")),
                    reported_status=r["reported_status"],
                    reported_at=datetime.fromisoformat(r["reported_at"].replace("Z", "+00:00")),
                    audit_at=datetime.fromisoformat(r["audit_at"].replace("Z", "+00:00")),
                    request_text=r["request_text"],
                )
                self._requests[req.case_id] = req

    @property
    def engine(self) -> AuditEngine:
        if self._engine is None:
            self._engine = AuditEngine(self.dataset_dir)
        return self._engine

    def list_cases(self, offset: int = 0, limit: int = 50, search: str | None = None, status: str | None = None) -> tuple[int, list[CaseSummary]]:
        filtered = list(self._requests.values())
        if search:
            q = search.lower()
            filtered = [r for r in filtered if q in r.case_id.lower() or q in r.email.lower()]
        if status:
            filtered = [r for r in filtered if (self._results.get(r.case_id).status if r.case_id in self._results else None) == status]
        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        summaries = [
            CaseSummary(
                case_id=r.case_id,
                email=r.email,
                requested_at=r.requested_at,
                reported_status=r.reported_status,
                audit_at=r.audit_at,
                status=self._results[r.case_id].status if r.case_id in self._results else None,
            )
            for r in paginated
        ]
        return total, summaries

    def get_case(self, case_id: str) -> CaseDetailResponse | None:
        req = self._requests.get(case_id)
        if not req:
            return None
        res = self._results.get(case_id) or self.engine.audit_case(req)
        self._results[case_id] = res
        return CaseDetailResponse(
            case_id=req.case_id,
            email=req.email,
            requested_at=req.requested_at,
            reported_status=req.reported_status,
            reported_at=req.reported_at,
            audit_at=req.audit_at,
            request_text=req.request_text,
            status=res.status,
            steps=res.steps,
        )

    def audit_single_case(self, case_id: str) -> CaseDetailResponse | None:
        req = self._requests.get(case_id)
        if not req:
            return None
        res = self.engine.audit_case(req)
        self._results[case_id] = res
        return self.get_case(case_id)

    def run_all(self, output_path: Path | str = "output.csv") -> tuple[dict[str, int], float]:
        t0 = time.time()
        results = [self.engine.audit_case(req) for req in self._requests.values()]
        for res in results:
            self._results[res.case_id] = res
        write_output_csv(results, output_path, expected_count=len(self._requests))
        counts = {
            "total_cases": len(results),
            "complete": sum(1 for r in results if r.status == "COMPLETE"),
            "incomplete": sum(1 for r in results if r.status == "INCOMPLETE"),
            "not_applicable": sum(1 for r in results if r.status == "NOT_APPLICABLE"),
        }
        return counts, time.time() - t0

    def get_stats(self) -> StatsResponse:
        if not self._results:
            self.run_all()
        counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
        ops: dict[str, int] = {}
        for r in self._results.values():
            counts[r.status] = counts.get(r.status, 0) + 1
            for s in r.steps:
                if s.phase == "FINDING":
                    ops[s.operation] = ops.get(s.operation, 0) + 1
        return StatsResponse(
            total_cases=len(self._requests),
            complete_count=counts["COMPLETE"],
            incomplete_count=counts["INCOMPLETE"],
            not_applicable_count=counts["NOT_APPLICABLE"],
            findings_by_operation=ops,
        )

_service: AuditService | None = None

def get_audit_service() -> AuditService:
    global _service
    if _service is None:
        _service = AuditService()
    return _service
