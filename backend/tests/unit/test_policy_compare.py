from backend.agent.models import ResourceState
from backend.agent.stages.s6_policy import derive_treatments
from backend.agent.stages.s7_compare import compare_states_and_treatments
from backend.agent.stages.s8_status import decide_status
from backend.config.loader import load_operations_config

def test_policy_compare_case_01_complete():
    cfg = load_operations_config()
    rules = {"USER_PROFILE": "DELETE"}
    states = [
        ResourceState(key=("account_service", "account_001"), category="USER_PROFILE", kind="record", state="ABSENT", evidence_id="evidence_54")
    ]
    treatments, gate6 = derive_treatments(states, rules, cfg)
    assert gate6.ok is True
    assert treatments[0].target_state == "ABSENT"

    findings, gate7 = compare_states_and_treatments(states, treatments, cfg)
    assert gate7.ok is True
    assert len(findings) == 0

    status, gate8 = decide_status(is_deletion=True, findings=findings, states=states)
    assert gate8.ok is True
    assert status == "COMPLETE"

def test_policy_compare_case_11_incomplete():
    cfg = load_operations_config()
    rules = {
        "USER_PROFILE": "DELETE",
        "SEARCH_INDEX_ENTRY": "DELETE",
        "ANALYTICS_PROFILE": "ANONYMIZE",
        "SUPPORT_MESSAGE": "REDACT",
        "SECURITY_AUDIT_LOG": "RETAIN",
    }
    states = [
        ResourceState(key=("search_service", "search_052"), category="SEARCH_INDEX_ENTRY", kind="record", state="PRESENT", evidence_id="evidence_03"),
        ResourceState(key=("analytics_platform", "analytics_2034"), category="ANALYTICS_PROFILE", kind="record", state="IDENTIFIABLE", evidence_id="evidence_03"),
        ResourceState(key=("support_platform", "support_864"), category="SUPPORT_MESSAGE", kind="record", state="IDENTIFIABLE", evidence_id="evidence_03"),
        ResourceState(key=("integration_service", "data_flow_9522"), category="DATA_FLOW", kind="flow", state="ACTIVE", evidence_id="evidence_03"),
        ResourceState(key=("account_service", "account_4248"), category="USER_PROFILE", kind="record", state="ABSENT", evidence_id="evidence_03"),
    ]
    treatments, _ = derive_treatments(states, rules, cfg)
    findings, _ = compare_states_and_treatments(states, treatments, cfg)
    
    assert len(findings) == 4
    finding_ops = {f.operation for f in findings}
    assert "REPORT_REMAINING_RECORD" in finding_ops
    assert "REPORT_EXPOSED_PII" in finding_ops
    assert "REPORT_ACTIVE_DATA_FLOW" in finding_ops

    status, _ = decide_status(is_deletion=True, findings=findings, states=states)
    assert status == "INCOMPLETE"

def test_policy_compare_case_14_backup_risk():
    cfg = load_operations_config()
    states = [
        ResourceState(key=("backup_service", "backup_3870"), category="BACKUP_ARCHIVE", kind="restore_path", state="ACTIVE", evidence_id="evidence_03")
    ]
    treatments, _ = derive_treatments(states, {}, cfg)
    findings, _ = compare_states_and_treatments(states, treatments, cfg)
    
    assert len(findings) == 1
    assert findings[0].operation == "REPORT_RESTORE_RISK"
    status, _ = decide_status(is_deletion=True, findings=findings, states=states)
    assert status == "INCOMPLETE"

def test_policy_compare_non_deletion_not_applicable():
    status, _ = decide_status(is_deletion=False, findings=[], states=[])
    assert status == "NOT_APPLICABLE"
