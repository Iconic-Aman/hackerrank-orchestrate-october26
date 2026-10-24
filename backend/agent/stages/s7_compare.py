from __future__ import annotations
from pydantic import BaseModel, Field
from backend.agent.models import Finding, ResourceState, Treatment
from backend.config.loader import OperationsConfig

class Gate7Result(BaseModel):
    ok: bool
    findings_count: int = 0
    errors: list[str] = Field(default_factory=list)

def compare_states_and_treatments(
    states: list[ResourceState],
    treatments: list[Treatment],
    ops_cfg: OperationsConfig,
) -> tuple[list[Finding], Gate7Result]:
    findings: list[Finding] = []
    treatment_by_key = {t.key: t for t in treatments}
    strength_map = ops_cfg.strength

    for state in states:
        treatment = treatment_by_key.get(state.key)
        if not treatment:
            continue

        target = treatment.target_state
        curr = state.state
        ev_id = state.evidence_id or ""

        # Check satisfaction
        if target == "ABSENT":
            if curr != "ABSENT":
                findings.append(Finding(key=state.key, operation="REPORT_REMAINING_RECORD", state="PRESENT", evidence_id=ev_id))
        elif target in ("REDACTED", "ANONYMIZED"):
            # Stronger state satisfies weaker (e.g. ABSENT satisfies REDACTED)
            curr_str = strength_map.get(curr, 0)
            target_str = strength_map.get(target, 1)
            if curr in ("PRESENT", "IDENTIFIABLE") or state.exposed_fields or curr_str < target_str:
                findings.append(Finding(key=state.key, operation="REPORT_EXPOSED_PII", state="PRESENT", evidence_id=ev_id))
        elif target == "DISABLED":
            if curr == "ACTIVE":
                findings.append(Finding(key=state.key, operation="REPORT_ACTIVE_DATA_FLOW", state="ACTIVE", evidence_id=ev_id))
        elif target == "BLOCKED":
            if curr == "ACTIVE":
                findings.append(Finding(key=state.key, operation="REPORT_RESTORE_RISK", state="ACTIVE", evidence_id=ev_id))
        elif target == "PRESENT":
            if curr != "PRESENT":
                findings.append(Finding(key=state.key, operation="REPORT_REMAINING_RECORD", state="ABSENT", evidence_id=ev_id))

    gate7 = Gate7Result(ok=True, findings_count=len(findings))
    return findings, gate7
