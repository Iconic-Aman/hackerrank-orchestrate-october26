import argparse
import sys
from pathlib import Path

# Add repo root and code directory to sys.path
repo_root = Path(__file__).resolve().parent.parent
code_dir = Path(__file__).resolve().parent
for p in (repo_root, code_dir):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.agent.pipeline import AuditEngine

def main():
    parser = argparse.ArgumentParser(description="Ghost Data Audit Agent CLI")
    parser.add_argument("--dataset", default=str(repo_root / "dataset"), help="Path to dataset directory")
    parser.add_argument("--input", default=str(repo_root / "dataset" / "deletion_requests.csv"), help="Input CSV path")
    parser.add_argument("--output", default=str(repo_root / "output.csv"), help="Output CSV path")
    args = parser.parse_args()

    print(f"Initializing AuditEngine on {args.dataset}...")
    engine = AuditEngine(dataset_dir=args.dataset)
    print(f"Auditing cases from {args.input}...")
    results = engine.run_all(requests_csv=args.input, output_csv=args.output)
    print(f"Completed {len(results)} cases. Output written to {args.output}")

if __name__ == "__main__":
    main()
