import csv
from pathlib import Path
from backend.agent.pipeline import AuditEngine

def test_golden_sample_accuracy(tmp_path):
    engine = AuditEngine(dataset_dir="dataset")
    out_csv = tmp_path / "sample_out.csv"
    results = engine.run_all("dataset/sample_deletion_requests.csv", out_csv)

    golden = {
        r["case_id"]: r["deletion_status"]
        for r in csv.DictReader(open("dataset/sample_output.csv", encoding="utf-8"))
    }
    actual = {r.case_id: r.status for r in results}

    matches = sum(golden[cid] == actual[cid] for cid in golden)
    accuracy = matches / len(golden)
    # Baseline test gate: must achieve at least 50% accuracy on first end-to-end integration
    assert accuracy >= 0.50
