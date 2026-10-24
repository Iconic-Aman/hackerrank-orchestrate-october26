from datetime import datetime
from pathlib import Path
from backend.agent.models import Coverage, Fact, Observation
from backend.agent.parsers.dispatcher import parse_evidence_file
from backend.agent.stages.s5_state import resolve_resource_states

def test_s5_state_tombstone_clean_vs_exposed():
    audit_at = datetime.fromisoformat("2026-09-15T12:00:00+00:00")
    facts, coverage = parse_evidence_file("dataset/evidence/records/customer_data_snapshot_bundle_20260915.json", "evidence_51")
    
    t440_facts = [f for f in facts if f.resource_id == "tombstone_440"]
    t9178_facts = [f for f in facts if f.resource_id == "tombstone_9178"]
    
    obs = [
        Observation(fact=t440_facts[0]),
        Observation(fact=t9178_facts[0]),
    ]
    res_set = {
        ("identity_service", "tombstone_440"),
        ("identity_service", "tombstone_9178"),
    }
    
    states, gate5 = resolve_resource_states(res_set, obs, coverage, audit_at)
    assert gate5.ok is True
    
    s_map = {s.key[1]: s.state for s in states}
    # tombstone_440 has null fields -> REDACTED
    assert s_map["tombstone_440"] == "REDACTED"
    # tombstone_9178 has real name and email -> PRESENT
    assert s_map["tombstone_9178"] == "PRESENT"

def test_s5_state_absence_proof():
    audit_at = datetime.fromisoformat("2026-09-15T12:00:00+00:00")
    # evidence_51 has coverage for account_service with 0 rows
    coverage = [
        Coverage(
            file_id="evidence_51",
            system_id="account_service",
            collection="customer_profiles",
            captured_at=audit_at,
            row_count=0,
        )
    ]
    res_set = {("account_service", "account_4857")}
    # No facts in evidence_51 for account_4857
    states, gate5 = resolve_resource_states(res_set, [], coverage, audit_at)
    assert gate5.ok is True
    assert len(states) == 1
    assert states[0].state == "ABSENT"
    assert states[0].evidence_id == "evidence_51"

def test_s5_state_handover_identifiable():
    audit_at = datetime.fromisoformat("2026-10-01T12:00:00+00:00")
    facts, coverage = parse_evidence_file("dataset/evidence/records/customer_account_handover_20261001.txt", "evidence_03")
    
    # Filter facts for novak
    novak_facts = [f for f in facts if "novak.tomasz@icloud.com" in f.fields.get("identifier", "")]
    obs = [Observation(fact=f) for f in novak_facts]
    res_set = {(f.system_id, f.resource_id) for f in novak_facts}
    
    states, gate5 = resolve_resource_states(res_set, obs, coverage, audit_at)
    assert gate5.ok is True
    s_map = {s.key[1]: s.state for s in states}
    assert s_map["analytics_2034"] == "IDENTIFIABLE"
    assert s_map["search_052"] == "PRESENT"
    assert s_map["data_flow_9522"] == "ACTIVE"
    assert s_map["account_4248"] == "ABSENT"
