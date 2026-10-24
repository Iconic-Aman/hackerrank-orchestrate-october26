from __future__ import annotations
import csv
import json
from pathlib import Path
from pydantic import BaseModel, Field
from backend.agent.models import CaseResult

class Gate10Result(BaseModel):
    ok: bool
    rows_written: int = 0
    errors: list[str] = Field(default_factory=list)

def serialize_steps(steps: list) -> str:
    if not steps:
        return "[]"
    raw_list = [s.model_dump() for s in steps]
    return json.dumps(raw_list, separators=(",", ":"))

def write_output_csv(
    results: list[CaseResult],
    output_path: Path | str,
    expected_count: int | None = None,
) -> Gate10Result:
    errors: list[str] = []
    out = Path(output_path)
    
    # Sort results by case_id
    sorted_results = sorted(results, key=lambda r: r.case_id)
    
    if expected_count is not None and len(sorted_results) != expected_count:
        errors.append(f"Row count mismatch: expected {expected_count}, got {len(sorted_results)}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        
        for r in sorted_results:
            steps_str = serialize_steps(r.steps)
            if r.status == "NOT_APPLICABLE" and steps_str != "[]":
                errors.append(f"Case {r.case_id} is NOT_APPLICABLE but has non-empty steps")
            writer.writerow([r.case_id, r.status, steps_str])

    # Re-read verification
    if not out.exists():
        errors.append(f"Output file was not created: {out}")
    else:
        with open(out, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            if len(reader) != len(sorted_results):
                errors.append(f"Written row count mismatch: {len(reader)} != {len(sorted_results)}")

    return Gate10Result(ok=(len(errors) == 0), rows_written=len(sorted_results), errors=errors)
