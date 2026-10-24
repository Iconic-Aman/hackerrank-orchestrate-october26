import json
from pathlib import Path
from backend.agent.models import CaseResult, Finding, ResourceState, Treatment
from backend.agent.stages.s9_plan import build_plan
from backend.agent.stages.s10_output import write_output_csv, serialize_steps
from backend.config.loader import load_operations_config

def test_s9_plan_case_11_golden():
    cfg = load_operations_config()
    states = [
        ResourceState(key=("search_service", "search_052"), category="SEARCH_INDEX_ENTRY", kind="record", state="PRESENT", evidence_id="evidence_03"),
        ResourceState(key=("analytics_platform", "analytics_2034"), category="ANALYTICS_PROFILE", kind="record", state="IDENTIFIABLE", evidence_id="evidence_03"),
        ResourceState(key=("support_platform", "support_864"), category="SUPPORT_MESSAGE", kind="record", state="IDENTIFIABLE", evidence_id="evidence_03"),
        ResourceState(key=("integration_service", "data_flow_9522"), category="DATA_FLOW", kind="flow", state="ACTIVE", evidence_id="evidence_03"),
        ResourceState(key=("account_service", "account_4248"), category="USER_PROFILE", kind="record", state="ABSENT", evidence_id="evidence_03"),
        ResourceState(key=("security_service", "audit_record_9394"), category="SECURITY_AUDIT_LOG", kind="record", state="PRESENT", evidence_id="evidence_03"),
    ]
    treatments = [
        Treatment(key=("search_service", "search_052"), action="DELETE", kind="record", target_state="ABSENT"),
        Treatment(key=("analytics_platform", "analytics_2034"), action="ANONYMIZE", kind="record", target_state="ANONYMIZED"),
        Treatment(key=("support_platform", "support_864"), action="REDACT", kind="record", target_state="REDACTED"),
        Treatment(key=("integration_service", "data_flow_9522"), action="*", kind="flow", target_state="DISABLED"),
        Treatment(key=("account_service", "account_4248"), action="DELETE", kind="record", target_state="ABSENT"),
        Treatment(key=("security_service", "audit_record_9394"), action="RETAIN", kind="record", target_state="PRESENT"),
    ]
    findings = [
        Finding(key=("search_service", "search_052"), operation="REPORT_REMAINING_RECORD", state="PRESENT", evidence_id="evidence_03"),
        Finding(key=("analytics_platform", "analytics_2034"), operation="REPORT_EXPOSED_PII", state="PRESENT", evidence_id="evidence_03"),
        Finding(key=("support_platform", "support_864"), operation="REPORT_EXPOSED_PII", state="PRESENT", evidence_id="evidence_03"),
        Finding(key=("integration_service", "data_flow_9522"), operation="REPORT_ACTIVE_DATA_FLOW", state="ACTIVE", evidence_id="evidence_03"),
    ]

    steps, gate9 = build_plan("INCOMPLETE", findings, states, treatments, cfg)
    assert gate9.ok is True
    assert len(steps) == 14

    # Verify operations sequence
    ops = [s.operation for s in steps]
    assert ops[:4] == ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW"]
    assert ops[4:8] == ["DISABLE_DATA_FLOW", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD"]
    assert ops[8:] == [
        "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT",
        "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED"
    ]

def test_s9_plan_case_01_complete():
    cfg = load_operations_config()
    states = [
        ResourceState(key=("account_service", "account_001"), category="USER_PROFILE", kind="record", state="ABSENT", evidence_id="evidence_54")
    ]
    treatments = [
        Treatment(key=("account_service", "account_001"), action="DELETE", kind="record", target_state="ABSENT")
    ]
    steps, gate9 = build_plan("COMPLETE", [], states, treatments, cfg)
    assert gate9.ok is True
    assert len(steps) == 1
    assert steps[0].operation == "VERIFY_RECORD_ABSENT"
    assert steps[0].evidence_id == "evidence_54"

def test_s10_output_writer(tmp_path):
    results = [
        CaseResult(case_id="case_02", status="COMPLETE", steps=[]),
        CaseResult(case_id="case_01", status="NOT_APPLICABLE", steps=[]),
    ]
    out_file = tmp_path / "test_out.csv"
    gate10 = write_output_csv(results, out_file, expected_count=2)
    assert gate10.ok is True

    with open(out_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    assert lines[0] == "case_id,deletion_status,steps_json"
    assert lines[1] == "case_01,NOT_APPLICABLE,[]"
    assert lines[2] == "case_02,COMPLETE,[]"
