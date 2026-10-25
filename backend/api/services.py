from __future__ import annotations
import csv
import json
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

    def evaluate_dataset(self, dataset: str = "samples", refresh: bool = False) -> dict:
        if not hasattr(self, "_eval_cache"):
            self._eval_cache: dict[str, dict] = {}

        if not refresh and dataset in self._eval_cache:
            return self._eval_cache[dataset]

        sample_req_path = self.dataset_dir / "sample_deletion_requests.csv"
        sample_out_path = self.dataset_dir / "sample_output.csv"

        if not sample_req_path.exists() or not sample_out_path.exists():
            return {
                "dataset": dataset,
                "total_cases": 0,
                "passed_cases": 0,
                "failed_count": 0,
                "status_accuracy": 0.0,
                "step_accuracy": 0.0,
                "field_accuracy": 0.0,
                "sequence_accuracy": 0.0,
                "dev_score": 0.0,
                "holdout_score": 0.0,
                "cases": [],
                "failed_cases": [],
            }

        # Load golden ground truth
        golden: dict[str, dict] = {}
        with open(sample_out_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row["case_id"]
                try:
                    steps = json.loads(row["steps_json"])
                except Exception:
                    steps = []
                golden[cid] = {
                    "status": row["deletion_status"],
                    "steps": steps,
                }

        # Load sample requests
        sample_requests: list[Request] = []
        with open(sample_req_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sample_requests.append(
                    Request(
                        case_id=r["case_id"],
                        email=r["email"],
                        requested_at=datetime.fromisoformat(r["requested_at"].replace("Z", "+00:00")),
                        reported_status=r["reported_status"],
                        reported_at=datetime.fromisoformat(r["reported_at"].replace("Z", "+00:00")),
                        audit_at=datetime.fromisoformat(r["audit_at"].replace("Z", "+00:00")),
                        request_text=r["request_text"],
                    )
                )

        eval_cases = []
        failed_cases = []
        status_matches = 0
        total_steps_evaluated = 0
        matching_steps_count = 0
        fields_matched = 0
        fields_total = 0
        sequence_correct_cases = 0

        for req in sample_requests:
            cid = req.case_id
            g = golden.get(cid, {"status": "UNKNOWN", "steps": []})
            exp_status = g["status"]
            exp_steps = g["steps"]

            # Run agent audit on this case
            res = self.engine.audit_case(req)
            act_status = res.status
            act_steps = [s.model_dump() for s in res.steps]

            status_match = (act_status == exp_status)
            if status_match:
                status_matches += 1

            # Sequence check: FINDING -> REMEDIATION -> VERIFICATION
            phases = [s.get("phase") for s in act_steps]
            valid_seq = True
            phase_order = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}
            current_phase_rank = 0
            for p in phases:
                rank = phase_order.get(p, 0)
                if rank < current_phase_rank:
                    valid_seq = False
                    break
                current_phase_rank = rank
            if valid_seq:
                sequence_correct_cases += 1

            # Step overlap comparison
            exp_set = {(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation")) for s in exp_steps}
            act_set = {(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation")) for s in act_steps}
            overlap = len(exp_set & act_set)
            union = len(exp_set | act_set)

            if not exp_steps and not act_steps:
                step_match = status_match
                step_sim = 1.0 if status_match else 0.0
            else:
                step_sim = overlap / max(1, union)
                step_match = (step_sim >= 0.85 and status_match)

            total_steps_evaluated += max(len(exp_steps), len(act_steps))
            matching_steps_count += overlap

            # Field level comparison on aligned steps
            for es in exp_steps:
                fields_total += 5
                for as_ in act_steps:
                    if as_.get("resource_id") == es.get("resource_id") and as_.get("phase") == es.get("phase") and as_.get("operation") == es.get("operation"):
                        if as_.get("operation") == es.get("operation"):
                            fields_matched += 1
                        if as_.get("phase") == es.get("phase"):
                            fields_matched += 1
                        if as_.get("state") == es.get("state"):
                            fields_matched += 1
                        if as_.get("system_id") == es.get("system_id"):
                            fields_matched += 1
                        if as_.get("resource_id") == es.get("resource_id"):
                            fields_matched += 1
                        break

            case_passed = status_match and step_match
            reason = "Matches ground truth"
            if not status_match:
                reason = f"Status mismatch: expected {exp_status}, agent gave {act_status}"
            elif not step_match:
                reason = f"Step plan deviation: expected {len(exp_steps)} steps, agent generated {len(act_steps)} steps"

            case_data = {
                "case_id": cid,
                "email": req.email,
                "expected_status": exp_status,
                "actual_status": act_status,
                "status_match": status_match,
                "step_match": step_match,
                "score": round(100.0 if case_passed else (step_sim * 100.0 if status_match else 0.0), 1),
                "reason": reason,
                "expected_steps": exp_steps,
                "actual_steps": act_steps,
            }
            eval_cases.append(case_data)

            if not case_passed:
                failed_cases.append({
                    "case_id": cid,
                    "email": req.email,
                    "reason": reason,
                    "expected_status": exp_status,
                    "actual_status": act_status,
                    "expected_steps": exp_steps,
                    "actual_steps": act_steps,
                })

        num_cases = len(sample_requests)
        status_acc = status_matches / max(1, num_cases)
        step_acc = matching_steps_count / max(1, total_steps_evaluated) if total_steps_evaluated > 0 else 1.0
        field_acc = fields_matched / max(1, fields_total) if fields_total > 0 else 1.0
        seq_acc = sequence_correct_cases / max(1, num_cases)

        result = {
            "dataset": dataset,
            "total_cases": num_cases,
            "passed_cases": num_cases - len(failed_cases),
            "failed_count": len(failed_cases),
            "status_accuracy": round(status_acc, 4),
            "step_accuracy": round(step_acc, 4),
            "field_accuracy": round(field_acc, 4),
            "sequence_accuracy": round(seq_acc, 4),
            "dev_score": round(status_acc * 100, 1),
            "holdout_score": round((status_acc * 0.6 + step_acc * 0.4) * 100, 1),
            "cases": eval_cases,
            "failed_cases": failed_cases,
        }
        self._eval_cache[dataset] = result
        return result


_service: AuditService | None = None

def get_audit_service() -> AuditService:
    global _service
    if _service is None:
        _service = AuditService()
    return _service
