from __future__ import annotations
import csv
import json
from pathlib import Path

def test_submission_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    output_path = root / "output.csv"
    requests_path = root / "dataset" / "deletion_requests.csv"

    assert output_path.exists(), "output.csv missing at repo root"

    with open(requests_path, "r", encoding="utf-8") as f:
        expected_ids = [r["case_id"] for r in csv.DictReader(f)]

    with open(output_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 518, f"Expected 518 rows, got {len(reader)}"
    assert [r["case_id"] for r in reader] == sorted(expected_ids), "case_id mismatch or wrong order"

    allowed_statuses = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
    allowed_phases = ["FINDING", "REMEDIATION", "VERIFICATION"]

    for row in reader:
        assert row["deletion_status"] in allowed_statuses
        steps = json.loads(row["steps_json"])
        assert isinstance(steps, list)

        if row["deletion_status"] == "NOT_APPLICABLE":
            assert steps == [], f"Case {row['case_id']} NOT_APPLICABLE must have empty steps"
            continue

        for i, step in enumerate(steps, 1):
            assert step["step_no"] == i
            assert step["phase"] in allowed_phases
            if row["deletion_status"] == "COMPLETE":
                assert step["phase"] == "VERIFICATION"
                assert step["evidence_id"] != ""
            elif step["phase"] in ("REMEDIATION", "VERIFICATION"):
                assert step["evidence_id"] == ""