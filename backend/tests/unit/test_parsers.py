from datetime import datetime
from pathlib import Path
from backend.agent.parsers.dispatcher import parse_evidence_file

def test_parse_pipe_table_evidence_03():
    path = Path("dataset/evidence/records/customer_account_handover_20261001.txt")
    facts, coverage = parse_evidence_file(path, file_id="evidence_03")
    assert len(facts) > 0
    assert len(coverage) > 0
    # Check novak.tomasz record exists
    novak_facts = [f for f in facts if "novak.tomasz@icloud.com" in f.fields.get("identifier", "")]
    assert len(novak_facts) >= 4

def test_parse_json_bundle_evidence_51():
    path = Path("dataset/evidence/records/customer_data_snapshot_bundle_20260915.json")
    facts, coverage = parse_evidence_file(path, file_id="evidence_51")
    assert len(facts) > 0
    # Must have coverage for account_service with 0 rows (proves absence!)
    acc_cov = [c for c in coverage if c.system_id == "account_service"]
    assert len(acc_cov) == 1
    assert acc_cov[0].row_count == 0

def test_parse_sql_snapshot_evidence_54():
    path = Path("dataset/evidence/databases/customer_accounts_failover_replica_20260902.sql")
    sys_map = {"account": "account_service"}
    facts, coverage = parse_evidence_file(path, file_id="evidence_54", resource_system_map=sys_map)
    assert len(facts) > 0
    assert len(coverage) > 0
    # Ensure Leila Haddad row parsed
    leila_facts = [f for f in facts if f.resource_id == "account_005"]
    assert len(leila_facts) == 1
    assert leila_facts[0].system_id == "account_service"

def test_parse_log_evidence_61():
    path = Path("dataset/evidence/logs/support_replica.log")
    sys_map = {"support": "support_platform"}
    facts, coverage = parse_evidence_file(path, file_id="evidence_61", resource_system_map=sys_map)
    assert len(facts) > 0
    # Check support_002 is captured
    s002 = [f for f in facts if f.resource_id == "support_002"]
    assert len(s002) > 0
