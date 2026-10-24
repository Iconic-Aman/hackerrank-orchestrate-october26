import json
from pathlib import Path
from backend.agent.models import Step, CaseResult
from backend.config.loader import load_operations_config

def test_load_operations_config():
    cfg = load_operations_config()
    assert "FINDING" in cfg.phases
    assert "VERIFICATION" in cfg.phases
    assert "REPORT_REMAINING_RECORD" in cfg.operations
    assert cfg.operations["REPORT_REMAINING_RECORD"].state == "PRESENT"
    assert len(cfg.treatments) > 0

def test_validate_sample_steps():
    raw_step = {
        "step_no": 1,
        "phase": "VERIFICATION",
        "system_id": "account_service",
        "resource_id": "account_001",
        "operation": "VERIFY_RECORD_ABSENT",
        "state": "ABSENT",
        "evidence_id": "evidence_54",
    }
    step = Step.model_validate(raw_step)
    assert step.step_no == 1
    assert step.state == "ABSENT"

def test_validate_sample_case_result():
    res = CaseResult(
        case_id="case_01",
        status="COMPLETE",
        steps=[
            Step(
                step_no=1,
                phase="VERIFICATION",
                system_id="account_service",
                resource_id="account_001",
                operation="VERIFY_RECORD_ABSENT",
                state="ABSENT",
                evidence_id="evidence_54",
            )
        ],
    )
    assert res.status == "COMPLETE"
    assert len(res.steps) == 1
